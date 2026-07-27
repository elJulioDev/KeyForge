"""
Componente para gestionar múltiples reglas de remapeo
"""
import ttkbootstrap as ttk
from tkinter import messagebox
from .components import CommonKeysWindow
from ..utils import WindowManager, get_icon


class RulesManagerComponent:
    """Gestor visual de reglas de remapeo con tabla Treeview"""
    
    def __init__(self, parent, tr, on_detect_key_callback):
        self.parent = parent
        self.tr = tr
        self.on_detect_key = on_detect_key_callback
        self.selected_index = None
        self.current_rules = [] # Almacén local de reglas para edición
        
        self._create_ui()
    
    def _create_ui(self):
        """Crea la interfaz del gestor de reglas"""
        # Usamos un Frame normal en lugar de Labelframe para que se integre mejor en la pestaña
        self.frame = ttk.Frame(self.parent, padding=10)
        self.frame.pack(fill="both", expand=True)
        
        # --- BARRA DE HERRAMIENTAS (Arriba) ---
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            toolbar, 
            text=self.tr.get("rules_title", "Remap Rules"), 
            font=("-size", 12, "-weight", "bold")
        ).pack(side="left")

        # Botones alineados a la derecha
        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side="right")

        icon_delete = get_icon("trash-2", 14, "#FFFFFF")
        icon_edit = get_icon("pencil", 14, "#FFFFFF")
        icon_add = get_icon("plus", 14, "#FFFFFF")

        btn_delete = ttk.Button(
            btn_frame,
            text=self.tr.get("delete_rule_btn", "Delete"),
            image=icon_delete, compound="left",
            bootstyle="danger",
            command=self._delete_rule
        )
        btn_delete.image = icon_delete
        btn_delete.pack(side="right", padx=5)

        btn_edit = ttk.Button(
            btn_frame,
            text=self.tr.get("edit_rule_btn", "Edit"),
            image=icon_edit, compound="left",
            bootstyle="info",
            command=self._edit_rule_dialog
        )
        btn_edit.image = icon_edit
        btn_edit.pack(side="right", padx=5)
        
        btn_add = ttk.Button(
            btn_frame,
            text=self.tr.get("add_rule_btn", "Add"),
            image=icon_add, compound="left",
            bootstyle="success",
            command=self._add_rule_dialog
        )
        btn_add.image = icon_add
        btn_add.pack(side="right", padx=5)
        
        # --- TABLA ---
        tree_frame = ttk.Frame(self.frame)
        tree_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        
        columns = ("source", "target", "mode", "status")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            yscrollcommand=scrollbar.set
        )
        
        self.tree.heading("source", text=self.tr.get("replace_label", "Input").replace(":", ""))
        self.tree.heading("target", text=self.tr.get("with_label", "Output").replace(":", ""))
        self.tree.heading("mode", text=self.tr.get("mode_title", "Mode"))
        self.tree.heading("status", text=self.tr.get("status_label", "Status"))

        colors = ttk.Style().colors
        self.tree.tag_configure("rule-enabled", foreground=colors.success)
        self.tree.tag_configure("rule-disabled", foreground=colors.danger)
        
        self.tree.column("source", width=100, anchor="center")
        self.tree.column("target", width=100, anchor="center")
        self.tree.column("mode", width=100, anchor="center")
        self.tree.column("status", width=60, anchor="center")
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.tree.yview)
        
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        # Doble clic para editar
        self.tree.bind("<Double-1>", lambda e: self._edit_rule_dialog())
        
        # Footer con tip
        ttk.Label(
            self.frame,
            text=self.tr.get("rules_tip", "Tip: Double click to edit a rule"),
            font=("-size", 8),
            bootstyle="secondary"
        ).pack(pady=(5, 0), anchor="w")
    
    def _on_select(self, event):
        selection = self.tree.selection()
        if selection:
            self.selected_index = self.tree.index(selection[0])
        else:
            self.selected_index = None
    
    def load_rules(self, rules):
        """Carga reglas en la tabla y guarda referencia"""
        self.current_rules = rules # Guardamos los objetos KeyRule
        
        # Limpiar y recargar
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for rule in rules:
            mode_text = self.tr.get("hold", "Hold") if rule.mode == "hold" else self.tr.get("toggle", "Toggle")
            status_text = "✓" if rule.enabled else "✕"
            status_tag = "rule-enabled" if rule.enabled else "rule-disabled"
            
            self.tree.insert("", "end", values=(
                rule.key_to_replace.upper(),
                rule.replacement_key.upper(),
                mode_text,
                status_text
            ), tags=(status_tag,))
            
    def _add_rule_dialog(self):
        RuleDialog(self.parent, self.tr, self.on_detect_key, callback=self._on_rule_added)
    
    def _edit_rule_dialog(self):
        if self.selected_index is None:
            messagebox.showwarning(self.tr.get("warning", "Warning"), self.tr.get("select_rule_msg", "Select a rule first"))
            return

        # RECUPERAR DATOS REALES PARA EDICIÓN
        try:
            rule_obj = self.current_rules[self.selected_index]
            rule_data = rule_obj.to_dict() # Convertir objeto a dict
            
            RuleDialog(
                self.parent, 
                self.tr, 
                self.on_detect_key, 
                rule_data=rule_data, 
                callback=self._on_rule_edited # Callback específico para editar
            )
        except IndexError:
            return

    def _on_rule_added(self, rule_data):
        if hasattr(self, 'on_add_rule'):
            self.on_add_rule(rule_data)

    def _on_rule_edited(self, rule_data):
        # Llamamos al callback de edición pasando el índice y los datos nuevos
        if hasattr(self, 'on_edit_rule'):
            self.on_edit_rule(self.selected_index, rule_data)

    def _delete_rule(self):
        if self.selected_index is None:
            return
        
        if hasattr(self, 'on_delete_rule'):
            self.on_delete_rule(self.selected_index)
            self.selected_index = None

    def set_controls_state(self, enabled):
        state = "normal" if enabled else "disabled"
        # Deshabilitar todos los botones dentro del toolbar
        for child in self.frame.winfo_children():
             if isinstance(child, ttk.Frame): # El toolbar
                 for btn in child.winfo_children():
                     if isinstance(btn, ttk.Button):
                         btn.config(state=state)

# --- CLASE RULE DIALOG (IGUAL QUE ANTES PERO COMPROBADO) ---
class RuleDialog:
    """Diálogo para crear/editar una regla"""
    
    def __init__(self, parent, tr, on_detect_key, rule_data=None, callback=None):
        self.parent = parent
        self.tr = tr
        self.on_detect_key = on_detect_key
        self.callback = callback
        self.rule_data = rule_data or {}
        self.window_manager = WindowManager()  # Instancia del manager
        
        self.dialog = ttk.Toplevel(parent)
        title = self.tr.get("edit_rule_title", "Edit Rule") if rule_data else self.tr.get("add_rule_title", "Add Rule")
        self.dialog.title(title)
        
        # ELIMINAMOS LA GEOMETRÍA FIJA AQUÍ
        # self.dialog.geometry(f"{w}x{h}") <-- BORRAR ESTO
        
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        
        self._create_ui()
        
        if rule_data:
            self._load_rule_data()
            
        # APLICAMOS EL AJUSTE AUTOMÁTICO AL FINAL
        self.window_manager.center_and_resize(self.dialog)
        # Aseguramos que quede por encima del root (fix stacking en Linux)
        self.window_manager.elevate(self.dialog, parent)
        self.window_manager.safe_grab_set(self.dialog)
    
    def _create_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        search_icon = get_icon("search", 14, ttk.Style().colors.secondary)

        # Inputs
        ttk.Label(main_frame, text=self.tr.get("replace_label", "Key to Replace:"), bootstyle="primary").pack(anchor="w")
        source_frame = ttk.Frame(main_frame)
        source_frame.pack(fill="x", pady=(5, 15))
        self.source_var = ttk.StringVar()
        ttk.Entry(source_frame, textvariable=self.source_var).pack(side="left", fill="x", expand=True, padx=(0,5))
        btn_detect_source = ttk.Button(source_frame, image=search_icon, command=lambda: self._detect_key(self.source_var), bootstyle="secondary-outline")
        btn_detect_source.image = search_icon
        btn_detect_source.pack(side="right")
        
        ttk.Label(main_frame, text=self.tr.get("with_label", "Replace with:"), bootstyle="primary").pack(anchor="w")
        target_frame = ttk.Frame(main_frame)
        target_frame.pack(fill="x", pady=(5, 10))
        self.target_var = ttk.StringVar()
        ttk.Entry(target_frame, textvariable=self.target_var).pack(side="left", fill="x", expand=True, padx=(0,5))
        btn_detect_target = ttk.Button(target_frame, image=search_icon, command=lambda: self._detect_key(self.target_var), bootstyle="secondary-outline")
        btn_detect_target.image = search_icon
        btn_detect_target.pack(side="right")

        ttk.Button(main_frame, text=self.tr.get("show_keys_btn", "Keyboard Map"), bootstyle="link", command=self._show_common_keys).pack(anchor="e")
        
        ttk.Separator(main_frame).pack(fill="x", pady=10)
        
        # Mode
        ttk.Label(main_frame, text=self.tr.get("mode_title", "Mode"), bootstyle="primary").pack(anchor="w", pady=(0,5))
        self.mode_var = ttk.StringVar(value="hold")
        ttk.Radiobutton(main_frame, text=self.tr.get("hold_mode", "Hold"), variable=self.mode_var, value="hold").pack(anchor="w", pady=2)
        ttk.Radiobutton(main_frame, text=self.tr.get("toggle_mode", "Toggle"), variable=self.mode_var, value="toggle").pack(anchor="w", pady=2)
        
        ttk.Separator(main_frame).pack(fill="x", pady=15)
        
        # Footer
        self.enabled_var = ttk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text=self.tr.get("rule_enabled", "Enabled"), variable=self.enabled_var, bootstyle="round-toggle").pack(side="left")
        
        ttk.Button(main_frame, text=self.tr.get("save_btn", "Save"), bootstyle="success", command=self._save).pack(side="right")

    def _detect_key(self, var):
        lbl = ttk.Label(self.dialog, text="Press any key...", bootstyle="inverse-danger")
        lbl.place(relx=0.5, rely=0.9, anchor="center")
        self.on_detect_key(lambda k, e: (var.set(k) if k else None, lbl.destroy()))

    def _show_common_keys(self):
        CommonKeysWindow(self.dialog, self.tr)

    def _load_rule_data(self):
        self.source_var.set(self.rule_data.get("key_to_replace", ""))
        self.target_var.set(self.rule_data.get("replacement_key", ""))
        self.mode_var.set(self.rule_data.get("mode", "hold"))
        self.enabled_var.set(self.rule_data.get("enabled", True))

    def _save(self):
        if not self.source_var.get() or not self.target_var.get():
            return
        data = {
            "key_to_replace": self.source_var.get().strip().lower(),
            "replacement_key": self.target_var.get().strip().lower(),
            "mode": self.mode_var.get(),
            "enabled": self.enabled_var.get()
        }
        if self.callback: self.callback(data)
        self.dialog.destroy()