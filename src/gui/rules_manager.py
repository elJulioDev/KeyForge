"""
Component for managing multiple remapping rules
"""
import ttkbootstrap as ttk
from tkinter import messagebox
from .components import CommonKeysWindow
from ..utils import WindowManager, get_icon


class RulesManagerComponent:
    """Visual manager for remapping rules with a Treeview table"""
    
    def __init__(self, parent, tr_manager, on_detect_key_callback):
        """Initialize the rules manager component."""
        self.parent = parent
        self.tr_manager = tr_manager
        self.tr = tr_manager
        self.on_detect_key = on_detect_key_callback
        self.selected_index = None
        self.current_rules = [] # Local store of rules for editing
        
        self._create_ui()
    
    def _create_ui(self):
        """Creates the rules manager interface"""
        # We use a normal Frame instead of a Labelframe so it integrates better into the tab
        self.frame = ttk.Frame(self.parent, padding=10)
        self.frame.pack(fill="both", expand=True)
        
        # --- TOOLBAR (Top) ---
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            toolbar, 
            text=self.tr("rules_title"), 
            font=("-size", 12, "-weight", "bold")
        ).pack(side="left")

        # Buttons aligned to the right
        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side="right")

        icon_delete = get_icon("trash-2", 22, "#FFFFFF")
        icon_edit = get_icon("pencil", 22, "#FFFFFF")
        icon_add = get_icon("plus", 22, "#FFFFFF")

        self.btn_delete = ttk.Button(
            btn_frame,
            text=self.tr("delete_rule_btn"),
            image=icon_delete, compound="left",
            bootstyle="danger",
            command=self._delete_rule
        )
        self.btn_delete.image = icon_delete
        self.btn_delete.pack(side="right", padx=5)

        self.btn_edit = ttk.Button(
            btn_frame,
            text=self.tr("edit_rule_btn"),
            image=icon_edit, compound="left",
            bootstyle="info",
            command=self._edit_rule_dialog
        )
        self.btn_edit.image = icon_edit
        self.btn_edit.pack(side="right", padx=5)
        
        self.btn_add = ttk.Button(
            btn_frame,
            text=self.tr("add_rule_btn"),
            image=icon_add, compound="left",
            bootstyle="success",
            command=self._add_rule_dialog
        )
        self.btn_add.image = icon_add
        self.btn_add.pack(side="right", padx=5)
        
        # --- TABLE ---
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        
        columns = ("source", "target", "mode")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            selectmode="browse",
            yscrollcommand=scrollbar.set
        )

        self.tree.heading("#0", text=self.tr("status_label"))
        self.tree.column("#0", width=60, anchor="center", stretch=False)

        self.tree.heading("source", text=self.tr("replace_label").replace(":", ""))
        self.tree.heading("target", text=self.tr("with_label").replace(":", ""))
        self.tree.heading("mode", text=self.tr("mode_title"))

        colors = ttk.Style().colors
        self.icon_enabled = get_icon("check", 20, colors.success)
        self.icon_disabled = get_icon("x", 20, colors.danger)
        self.tree.tag_configure("rule-enabled", foreground=colors.success)
        self.tree.tag_configure("rule-disabled", foreground=colors.danger)
        
        self.tree.column("source", width=100, anchor="center")
        self.tree.column("target", width=100, anchor="center")
        self.tree.column("mode", width=100, anchor="center")
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.tree.yview)
        
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        # Double click to edit
        self.tree.bind("<Double-1>", lambda e: self._edit_rule_dialog())
        
        # Footer with tip
        self.tip_label = ttk.Label(
            self.frame,
            text=self.tr("rules_tip"),
            font=("-size", 8),
            bootstyle="secondary"
        )
        self.tip_label.pack(pady=(5, 0), anchor="w")
    
    def _on_select(self, event):
        """Stores the selected row index."""
        selection = self.tree.selection()
        if selection:
            self.selected_index = self.tree.index(selection[0])
        else:
            self.selected_index = None
    
    def load_rules(self, rules):
        """Loads rules into the table and stores a reference"""
        self.current_rules = rules # We store the KeyRule objects
        
        # Clear and reload
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for rule in rules:
            mode_text = self.tr("hold") if rule.mode == "hold" else self.tr("toggle")
            status_icon = self.icon_enabled if rule.enabled else self.icon_disabled
            status_tag = "rule-enabled" if rule.enabled else "rule-disabled"
            
            self.tree.insert("", "end", image=status_icon, values=(
                rule.key_to_replace.upper(),
                rule.replacement_key.upper(),
                mode_text
            ), tags=(status_tag,))
    
    def _add_rule_dialog(self):
        """Opens the dialog to add a new rule."""
        RuleDialog(self.parent, self.tr_manager, self.on_detect_key, callback=self._on_rule_added)
    
    def _edit_rule_dialog(self):
        """Opens the dialog to edit the selected rule."""
        if self.selected_index is None:
            messagebox.showwarning(self.tr("warning"), self.tr("select_rule_msg"))
            return

        # RETRIEVE THE REAL DATA FOR EDITING
        try:
            rule_obj = self.current_rules[self.selected_index]
            rule_data = rule_obj.to_dict() # Convert object to dict
            
            RuleDialog(
                self.parent, 
                self.tr_manager, 
                self.on_detect_key, 
                rule_data=rule_data, 
                callback=self._on_rule_edited # Specific callback for editing
            )
        except IndexError:
            return

    def _on_rule_added(self, rule_data):
        """Forwards the newly added rule to the parent callback."""
        if hasattr(self, 'on_add_rule'):
            self.on_add_rule(rule_data)

    def _on_rule_edited(self, rule_data):
        # We call the edit callback passing the index and the new data
        if hasattr(self, 'on_edit_rule'):
            self.on_edit_rule(self.selected_index, rule_data)

    def _delete_rule(self):
        """Deletes the selected rule."""
        if self.selected_index is None:
            return
        
        if hasattr(self, 'on_delete_rule'):
            self.on_delete_rule(self.selected_index)
            self.selected_index = None

    def set_controls_state(self, enabled):
        """Enables or disables the toolbar buttons."""
        state = "normal" if enabled else "disabled"
        for btn in (self.btn_delete, self.btn_edit, self.btn_add):
            btn.config(state=state)

    def update_translations(self):
        """Updates headings, buttons and reloads rules"""
        # Table headings
        self.tree.heading("#0", text=self.tr("status_label"))
        self.tree.heading("source", text=self.tr("replace_label").replace(":", ""))
        self.tree.heading("target", text=self.tr("with_label").replace(":", ""))
        self.tree.heading("mode", text=self.tr("mode_title"))
        
        # Footer tip
        self.tip_label.config(text=self.tr("rules_tip"))
        
        # Toolbar buttons
        self.btn_delete.config(text=self.tr("delete_rule_btn"))
        self.btn_edit.config(text=self.tr("edit_rule_btn"))
        self.btn_add.config(text=self.tr("add_rule_btn"))
        
        # Reload rules with updated translations (hold/toggle mode)
        if self.current_rules:
            self.load_rules(self.current_rules)

# --- RULE DIALOG CLASS (SAME AS BEFORE BUT VERIFIED) ---
class RuleDialog:
    """Dialog to create/edit a rule"""
    
    def __init__(self, parent, tr_manager, on_detect_key, rule_data=None, callback=None):
        """Build the rule dialog."""
        self.parent = parent
        self.tr_manager = tr_manager
        self.tr = tr_manager
        self.on_detect_key = on_detect_key
        self.callback = callback
        self.rule_data = rule_data or {}
        self.window_manager = WindowManager()  # Manager instance
        
        self.dialog = ttk.Toplevel(parent)
        title = self.tr("edit_rule_title") if rule_data else self.tr("add_rule_title")
        self.dialog.title(title)
        
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        
        # Closing via the window X button must release the modal grab and
        # cancel any in-flight key detection, leaving no stuck state.
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._create_ui()
        
        if rule_data:
            self._load_rule_data()
            
        self.window_manager.center_and_resize(self.dialog)
        self.window_manager.elevate(self.dialog, parent)
        self.window_manager.safe_grab_set(self.dialog)

    def _on_close(self):
        """Closes the dialog, releasing the grab and cancelling detection."""
        try:
            self.dialog.grab_release()
        except Exception:
            pass
        try:
            if self.on_detect_key and hasattr(self, '_detect_lbl'):
                self._detect_lbl = None  # drop ref; <Destroy> handles cleanup
        except Exception:
            pass
        self.dialog.destroy()
    
    def _create_ui(self):
        """Creates the dialog UI."""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        search_icon = get_icon("search", 22, ttk.Style().colors.secondary)

        # Inputs
        ttk.Label(main_frame, text=self.tr("replace_label"), bootstyle="primary").pack(anchor="w")
        source_frame = ttk.Frame(main_frame)
        source_frame.pack(fill="x", pady=(5, 15))
        self.source_var = ttk.StringVar()
        ttk.Entry(source_frame, textvariable=self.source_var).pack(side="left", fill="x", expand=True, padx=(0,5))
        btn_detect_source = ttk.Button(source_frame, image=search_icon, command=lambda: self._detect_key(self.source_var), bootstyle="secondary-outline")
        btn_detect_source.image = search_icon
        btn_detect_source.pack(side="right")
        
        ttk.Label(main_frame, text=self.tr("with_label"), bootstyle="primary").pack(anchor="w")
        target_frame = ttk.Frame(main_frame)
        target_frame.pack(fill="x", pady=(5, 10))
        self.target_var = ttk.StringVar()
        ttk.Entry(target_frame, textvariable=self.target_var).pack(side="left", fill="x", expand=True, padx=(0,5))
        btn_detect_target = ttk.Button(target_frame, image=search_icon, command=lambda: self._detect_key(self.target_var), bootstyle="secondary-outline")
        btn_detect_target.image = search_icon
        btn_detect_target.pack(side="right")

        ttk.Button(main_frame, text=self.tr("show_keys_btn"), bootstyle="link", command=self._show_common_keys).pack(anchor="e")
        
        ttk.Separator(main_frame).pack(fill="x", pady=10)
        
        # Mode
        ttk.Label(main_frame, text=self.tr("mode_title"), bootstyle="primary").pack(anchor="w", pady=(0,5))
        self.mode_var = ttk.StringVar(value="hold")
        ttk.Radiobutton(main_frame, text=self.tr("hold_mode"), variable=self.mode_var, value="hold").pack(anchor="w", pady=2)
        ttk.Radiobutton(main_frame, text=self.tr("toggle_mode"), variable=self.mode_var, value="toggle").pack(anchor="w", pady=2)
        
        ttk.Separator(main_frame).pack(fill="x", pady=15)
        
        # Footer
        self.enabled_var = ttk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text=self.tr("rule_enabled"), variable=self.enabled_var, bootstyle="round-toggle").pack(side="left")
        
        ttk.Button(main_frame, text=self.tr("save_btn"), bootstyle="success", command=self._save).pack(side="right")

    def _detect_key(self, var):
        """Captures a pressed key and stores it in the given variable.
        The label is clickable to cancel; it is also removed when the
        key arrives or when the dialog is destroyed."""
        lbl = ttk.Label(self.dialog, text=self.tr("press_key_label"), bootstyle="inverse-danger")
        lbl.place(relx=0.5, rely=0.9, anchor="center")
        self._detect_lbl = lbl

        def cancel():
            try:
                if lbl.winfo_exists():
                    lbl.destroy()
            except Exception:
                pass

        # Clicking the label cancels detection (avoids a stuck label)
        lbl.bind("<Button-1>", lambda e: cancel())
        # Also clean up if the dialog is closed while detecting
        self.dialog.bind("<Destroy>", lambda e: cancel())

        def on_key(k, err):
            if k:
                try:
                    if self.dialog.winfo_exists():
                        var.set(k)
                except Exception:
                    pass
            cancel()

        self.on_detect_key(on_key)

    def _show_common_keys(self):
        """Opens the common keys reference window."""
        CommonKeysWindow(self.dialog, self.tr_manager)

    def _load_rule_data(self):
        """Populates the fields with the existing rule data."""
        self.source_var.set(self.rule_data.get("key_to_replace", ""))
        self.target_var.set(self.rule_data.get("replacement_key", ""))
        self.mode_var.set(self.rule_data.get("mode", "hold"))
        self.enabled_var.set(self.rule_data.get("enabled", True))

    def _save(self):
        """Collects the data and calls the callback, then closes the dialog."""
        source = self.source_var.get().strip().lower()
        target = self.target_var.get().strip().lower()
        if not source or not target:
            # Tell the user why Save did nothing instead of silently ignoring
            messagebox.showwarning(self.tr("warning"), self.tr("fill_fields_error"))
            return
        
        # Validate the key names against the keyboard library when possible.
        # If the library cannot validate (tables unavailable, e.g. Linux
        # without a dumpkeys cache), accept the input.
        for label, name in (("source", source), ("target", target)):
            if not self._is_known_key(name):
                messagebox.showwarning(
                    self.tr("warning"),
                    self.tr("invalid_key_msg", key=name, field=self.tr("replace_label" if label == "source" else "with_label"))
                )
                return
        
        data = {
            "key_to_replace": source,
            "replacement_key": target,
            "mode": self.mode_var.get(),
            "enabled": self.enabled_var.get()
        }
        if self.callback: self.callback(data)
        self.dialog.destroy()

    @staticmethod
    def _is_known_key(name: str) -> bool:
        """True when the keyboard library recognizes 'name' as a real key.
        Returns True (accept) if the library cannot validate at all."""
        try:
            import keyboard
            return bool(keyboard.key_to_scan_codes(name))
        except Exception:
            return True
