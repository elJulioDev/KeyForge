"""
Main window of the KeyForge application - Tabbed Design
"""
import ttkbootstrap as ttk
from tkinter import messagebox
import sys, os
from ..config import ConfigManager
from ..core import KeyHandler, AppMonitor
from ..utils import WindowManager
from ..utils import get_icon
from .components import (
    StatusComponent,
    AppFocusComponent,
    ControlButtonsComponent
)
from .rules_manager import RulesManagerComponent
from .minimized_window import MinimizedWindow
from .accessibility_settings import AccessibilityComponent
from ..utils.logger import get_logger
from src.config.constants import CURRENT_VERSION
from .splash_screen import SplashScreen

class KeyForgeApp:
    def __init__(self):
        """Initialize the main application window."""
        self.logger = get_logger()
        self.config_manager = ConfigManager()
        self.tr_manager = self.config_manager.tr_manager

        # Set up the theme before creating the window
        current_theme = self.config_manager.config.get("theme", "darkly")
        
        # 1. Create the window (but hidden)
        self._create_window(current_theme) 
        
        # ### CHANGE: Show the splash screen immediately after creating root
        # We pass the root so the splash inherits the theme
        self.splash = SplashScreen(
            self.root, 
            tr_manager=self.tr_manager,
            title="KeyForge", 
            version=CURRENT_VERSION
        )
        self.splash.update_step(5, self.tr_manager.tr("splash_config"))

        self.app_monitor = AppMonitor()
        self.key_handler = KeyHandler(self.app_monitor)
        self.window_manager = WindowManager()

        self.is_minimized = False
        self.minimized_window = None
        self.drag_data = {"x": 0, "y": 0}
        self.is_restarting = False
        
        # 2. Initial settings
        self.splash.update_step(20, self.tr_manager.tr("splash_gui"))
        self.key_handler.set_tk_root(self.root)

        self._create_ui_structure()
        self._load_initial_config()

        # 3. Schedule the heavy loading and splash completion
        self.root.after(100, self._post_initialization)

    def _load_initial_config(self):
        """Loads only the visually essential settings"""
        config = self.config_manager.config
        # Set quick visual values
        if self._app_focus_supported:
            self.app_focus_component.app_focus_var.set(config.get("enforce_app_focus", True))
            if config.get("target_app_name"):
                self.app_focus_component.set_app_name(config.get("target_app_name"))

    def _load_heavy_logic(self):
        """The rest of the configuration that requires processing"""
        config = self.config_manager.config
        
        # Configure monitor
        self.app_monitor.set_enforce_focus(config.get("enforce_app_focus", True))
        self.app_monitor.set_target_app(config.get("target_app_name", ""))
        
        # Load rules
        rules_data = config.get("rules", [])
        if rules_data:
            self.key_handler.load_rules(rules_data)
        self._refresh_rules_ui()
        
        # THIS IS THE KEY: Scanning windows is slow, now it is done here
        self._refresh_windows_list()
        self._toggle_app_focus()

    def _create_window(self, theme_name):
        """Create the main Tk window with the given theme."""
        self.root = ttk.Window(themename=theme_name)
        # No overrideredirect: we use the native OS title bar
        # to drag the window. Name and version go there.
        self.root.title(f"KeyForge v{CURRENT_VERSION}")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.iconphoto(True, get_icon("wrench", 64, "#3B82F6"))
        self.root.withdraw()

    def _post_initialization(self):
        """Heavy tasks and splash closing"""
    
        if hasattr(self, 'splash'): 
            self.splash.update_step(40, self.tr_manager.tr("splash_scan"))
        self._finalize_window_layout()
    
        if hasattr(self, 'splash'): 
            self.splash.update_step(60, self.tr_manager.tr("splash_rules"))
        self._load_heavy_logic()
    
        if hasattr(self, 'splash'): 
            self.splash.update_step(80, self.tr_manager.tr("splash_monitors"))
        self._init_monitoring()
    
        if hasattr(self, 'splash'): 
            self.splash.update_step(100, self.tr_manager.tr("splash_done"))
    
        self.root.after(500, self._finish_loading)
    
    def _finish_loading(self):
        """Closes the splash and shows the main window"""
        if hasattr(self, 'splash'):
            self.splash.close()
            del self.splash
        
        # Show main window
        self.root.deiconify() 
        # Make sure it is on top (once, without keeping it fixed topmost)
        self.root.lift()

    def _finalize_window_layout(self):
        """Calculates the ideal size based on the content of the tabs"""
        self.root.update_idletasks()
        
        # Get the required size
        req_w = self.root.winfo_reqwidth()
        req_h = self.root.winfo_reqheight()
        
        # Ensure a minimum width so it does not look too narrow
        final_w = max(req_w, 650) 
        # Ensure a minimum height
        final_h = max(req_h, 550)
        
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        
        x = int((screen_w / 2) - (final_w / 2))
        y = int((screen_h / 2) - (final_h / 2))
        
        self.root.geometry(f"{final_w}x{final_h}+{x}+{y}")

    def _create_ui_structure(self):
        """Build the tabbed UI structure and its components."""
        tr = self.tr_manager
        
        # --- MAIN BODY (Tabs) ---
        self.notebook = ttk.Notebook(self.root, bootstyle="primary")
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab 1: Dashboard
        self.tab_dashboard = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_dashboard, text=f" {tr('title')} ")
        
        # Tab 2: Rules
        self.tab_rules = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_rules, text=f" {tr('rules_title')} ")
        
        # Tab 3: Accessibility
        self.tab_accessibility = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_accessibility, text=f" {tr('accessibility_title')} ")

        # --- DASHBOARD CONTENT ---
        self.status_component = StatusComponent(self.tab_dashboard, tr)
        tr.subscribe(self.status_component)
        
        ttk.Separator(self.tab_dashboard).pack(fill="x", pady=15)
        
        self._app_focus_supported = self.app_monitor.supports_window_detection()
        if self._app_focus_supported:
            self.app_focus_component = AppFocusComponent(
                self.tab_dashboard, tr, 
                self._refresh_windows_list, self._toggle_app_focus, self._on_app_selected
            )
            tr.subscribe(self.app_focus_component)
            
            ttk.Separator(self.tab_dashboard).pack(fill="x", pady=15)

        self.control_buttons = ControlButtonsComponent(
            self.tab_dashboard, 
            tr,
            on_toggle_callback=self._toggle_script, 
            on_save_callback=self._save_config,
            on_minimize_callback=self._minimize_custom,
            on_exit_callback=self._on_close
        )
        tr.subscribe(self.control_buttons)

        # --- RULES CONTENT ---
        self.rules_manager = RulesManagerComponent(
            self.tab_rules, tr,
            on_detect_key_callback=self._on_detect_key_request
        )
        tr.subscribe(self.rules_manager)
        
        self.rules_manager.on_add_rule = self._add_rule_logic
        self.rules_manager.on_edit_rule = self._edit_rule_logic
        self.rules_manager.on_delete_rule = self._delete_rule_logic
        
        # --- ACCESSIBILITY CONTENT ---
        current_lang = self.config_manager.config.get("lang", "en")
        current_theme = self.config_manager.config.get("theme", "darkly")
        
        self.accessibility_component = AccessibilityComponent(
            self.tab_accessibility,
            tr,
            current_lang,
            current_theme,
            self._on_accessibility_change
        )
        tr.subscribe(self.accessibility_component)

    def _update_tab_labels(self):
        """Updates the notebook tab titles"""
        self.notebook.tab(0, text=f" {self.tr_manager.tr('title')} ")
        self.notebook.tab(1, text=f" {self.tr_manager.tr('rules_title')} ")
        self.notebook.tab(2, text=f" {self.tr_manager.tr('accessibility_title')} ")

    # --- Rules Logic ---
    
    def _add_rule_logic(self, rule_data):
        """Adds a rule and refreshes the rules UI."""
        success, error = self.key_handler.add_rule(
            rule_data['key_to_replace'], rule_data['replacement_key'],
            rule_data['mode'], rule_data['enabled']
        )
        if success: self._refresh_rules_ui()
        else: messagebox.showerror("Error", error)

    def _edit_rule_logic(self, index, rule_data):
        """Updates an existing rule in the core."""
        # Logic to update the existing rule in the core
        success, error = self.key_handler.update_rule(
            index,
            rule_data['key_to_replace'], rule_data['replacement_key'],
            rule_data['mode'], rule_data['enabled']
        )
        if success: self._refresh_rules_ui()
        else: messagebox.showerror("Error", error)

    def _delete_rule_logic(self, index):
        """Deletes a rule and refreshes the rules UI."""
        if self.key_handler.remove_rule(index): self._refresh_rules_ui()

    def _refresh_rules_ui(self):
        """Reloads the rules into the rules manager UI."""
        self.rules_manager.load_rules(self.key_handler.get_rules())

    def _on_detect_key_request(self, callback):
        """Delegates the key detection request to the key handler."""
        self.key_handler.listen_for_key(callback)

    # --- Core Logic & Config (Same as before) ---
    def _load_configuration(self):
        """Loads the full configuration into the components."""
        config = self.config_manager.config
        self.app_monitor.set_enforce_focus(config.get("enforce_app_focus", True) if self._app_focus_supported else False)
        self.app_monitor.set_target_app(config.get("target_app_name", "") if self._app_focus_supported else "")
        
        if self._app_focus_supported:
            self.app_focus_component.app_focus_var.set(config.get("enforce_app_focus", True))
            if config.get("target_app_name"):
                self.app_focus_component.set_app_name(config.get("target_app_name"))
            
        rules_data = config.get("rules", [])
        if rules_data:
            self.key_handler.load_rules(rules_data)
        
        self._refresh_rules_ui()
        self._refresh_windows_list()
        self._toggle_app_focus()

    def _save_config(self):
        """Saves the current configuration"""
        # 1. Get data from the CURRENT components
        if self._app_focus_supported:
            app_name = self.app_focus_component.get_app_name()
            enforce_focus = self.app_focus_component.is_focus_enabled()
        else:
            app_name, enforce_focus = "", False
        
        # 2. Get the rules directly from the handler (Core)
        # We no longer use key_config_component or mode_component
        rules_to_save = [rule.to_dict() for rule in self.key_handler.get_rules()]
        
        config_data = {
            "rules": rules_to_save,
            "enforce_app_focus": enforce_focus,
            "target_app_name": app_name if enforce_focus else ""
        }
        
        # 3. Save using the ConfigManager
        if self.config_manager.save_config(config_data):
            from ..config import CONFIG_FILE
            
            # 4. TRANSLATED success message
            title = self.tr_manager.tr("saved_title")
            
            # Get the translated template (e.g.: "Saved in:\n{configfile}")
            msg_template = self.tr_manager.tr("saved_msg")
            
            # Replace the placeholder with the real path
            msg = msg_template.replace("{configfile}", str(CONFIG_FILE))
            
            messagebox.showinfo(title, msg)

    def _init_monitoring(self):
        """Starts app monitoring, using events on Windows or polling otherwise."""
        def on_app_change(active):
            self.status_component.update_app_status(
                not self.app_monitor.enforce_app_focus, active, self.app_monitor.target_app_name
            )
        if sys.platform == 'win32':
            if self.app_monitor.use_event_monitoring(on_app_change): return
        self._start_polling_monitoring()

    def _start_polling_monitoring(self):
        """Polls the app monitor status periodically."""
        self.app_monitor.update_status()
        self.status_component.update_app_status(
            not self.app_monitor.enforce_app_focus, 
            self.app_monitor.target_app_is_active, 
            self.app_monitor.target_app_name
        )
        self._polling_id = self.root.after(500, self._start_polling_monitoring)

    # --- Accessibility ---
    
    def _on_accessibility_change(self, setting_type, value):
        """
        Callback when an accessibility setting changes.
        Language: hot-reload. Theme: restarts the application.
        """
        if hasattr(self, 'is_restarting') and self.is_restarting:
            return
        
        # Save the new value in the configuration
        config_update = {setting_type: value}
        
        # Preserve existing configuration
        config_update["rules"] = [rule.to_dict() for rule in self.key_handler.get_rules()]
        config_update["enforce_app_focus"] = (
            self.app_focus_component.is_focus_enabled() if self._app_focus_supported else False)
        config_update["target_app_name"] = (
            self.app_focus_component.get_app_name() if self._app_focus_supported else "")
        
        # Update the value that changed
        if setting_type == "lang":
            config_update["theme"] = self.config_manager.config.get("theme", "darkly")
        else:  # theme
            config_update["lang"] = self.config_manager.config.get("lang", "en")
        
        # Save configuration
        if self.config_manager.save_config(config_update):
            if setting_type == "lang":
                # HOT-RELOAD: Update the language without restarting
                self._reload_language(value)
            else:
                # Theme requires recreating the window
                self._restart_application()
    
    def _reload_language(self, new_lang):
        """Reloads translations and updates the UI without restarting"""
        # Save the current tab and polling state
        current_tab = self.notebook.index(self.notebook.select())
        
        # Notify the language change (subscribed components update themselves)
        changed = self.tr_manager.set_language(new_lang)
        
        # Update tab titles
        self._update_tab_labels()
        
        # Restore the selected tab
        if current_tab:
            self.notebook.select(current_tab)
        
        if changed:
            self.logger.info(f"Language changed to: {new_lang}")

    def _restart_application(self):
        """Restarts the application process completely"""
        if self.is_restarting:
            return

        self.is_restarting = True
        self.logger.info("Starting restart sequence...") # Informational log

        # 1. Save state and stop threads
        try:
            if self.key_handler.is_active():
                self.key_handler.stop()
            self._stop_all_monitoring()
        except Exception as e:
            # CHANGE: Use logger.error instead of print
            self.logger.error(f"Error cleaning up before restart: {e}")

        # 2. Destroy the current window
        try:
            self.root.destroy()
        except:
            pass

        # 3. ROBUST PROCESS RESTART
        # CHANGE: Use logger.info instead of print
        self.logger.info("Executing process restart...")
        
        if getattr(sys, 'frozen', False):
             # If it is an executable (PyInstaller)
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            # If it is a Python script (.py)
            os.execl(sys.executable, sys.executable, *sys.argv)

    def _stop_all_monitoring(self):
        """Stops all active monitoring systems"""
        try:
            # Stop polling if it exists
            if hasattr(self, '_polling_id'):
                self.root.after_cancel(self._polling_id)
                self._polling_id = None
        except:
            pass
    
        try:
            # Stop event monitoring
            if hasattr(self.app_monitor, 'stop_event_monitoring'):
                self.app_monitor.stop_event_monitoring()
        except:
            pass

    # --- Window Utilities ---
    def _refresh_windows_list(self):
        """Refreshes the window list in the app focus component."""
        if self._app_focus_supported:
            self.app_focus_component.update_app_list(self.app_monitor.get_all_windows())

    def _toggle_app_focus(self):
        """Enables or disables app focus enforcement in the UI."""
        if not self._app_focus_supported:
            return
        enforce = self.app_focus_component.is_focus_enabled()
        self.app_monitor.set_enforce_focus(enforce)
        if enforce:
            # Populate the window list when focus is enabled so the dropdown
            # is never empty; the list may not have been scanned yet.
            self._refresh_windows_list()
            self.app_focus_component.app_combo.config(state="readonly")
            self.app_focus_component.btn_refresh.config(state="normal")
        else:
            self.app_focus_component.app_combo.config(state="disabled")
            self.app_focus_component.btn_refresh.config(state="disabled")
        self.app_monitor.update_status()

    def _on_app_selected(self):
        """Updates the target app when a new app is selected."""
        if self._app_focus_supported and self.app_focus_component.is_focus_enabled():
            self.app_monitor.set_target_app(self.app_focus_component.get_app_name())
            self.app_monitor.update_status()

    def _start_drag(self, event):
        """Records the starting point of a window drag."""
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def _do_drag(self, event):
        """Moves the window according to the drag event."""
        x = self.root.winfo_x() + event.x - self.drag_data["x"]
        y = self.root.winfo_y() + event.y - self.drag_data["y"]
        self.root.geometry(f"+{x}+{y}")

    def _minimize_custom(self):
        """Minimizes the window to a floating icon preserving the visual position"""
        if self.is_minimized:
            return
        
        # CALCULATE CURRENT CENTER OF THE MAIN WINDOW
        # We do this BEFORE withdraw() to get the correct coordinates
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        
        center_x = root_x + (root_w / 2)
        center_y = root_y + (root_h / 2)
        
        self.root.withdraw()
        
        self.minimized_window = MinimizedWindow(
            self.root, 
            self._restore_window,
            self._toggle_script 
        )
        
        is_script_active = self.key_handler.is_active()
        
        # PASS THE CALCULATED CENTER TO SHOW()
        self.minimized_window.show(
            is_active=is_script_active, 
            center_pos=(center_x, center_y)
        )
        
        self.is_minimized = True

    def _toggle_script(self):
        """Starts or stops the key remapping script."""
        # Original logic to stop
        if self.key_handler.is_active():
            self.key_handler.stop()
            self.status_component.update_script_status(False)
            self.control_buttons.set_toggle_state(False)
            self.rules_manager.set_controls_state(True)
            if self._app_focus_supported:
                self.app_focus_component.set_controls_state(True)
            if self.is_minimized and self.minimized_window:
                self.minimized_window.update_visuals(False)
        else:
            # Original logic to start
            if not self.key_handler.get_rules():
                # If minimized and it errors, we show a simple popup because the main window is not visible
                messagebox.showwarning("KeyForge", self.tr_manager.tr("no_rules_msg"))
                return
            
            self.app_monitor.set_enforce_focus(
                self.app_focus_component.is_focus_enabled() if self._app_focus_supported else False)
            self.app_monitor.set_target_app(
                self.app_focus_component.get_app_name() if self._app_focus_supported else "")
            
            success, error = self.key_handler.start()
            if success:
                self.status_component.update_script_status(True, len(self.key_handler.get_rules()))
                self.control_buttons.set_toggle_state(True)
                self.rules_manager.set_controls_state(False)
                if self._app_focus_supported:
                    self.app_focus_component.set_controls_state(False)
                if self.is_minimized and self.minimized_window:
                    self.minimized_window.update_visuals(True)
            else:
                self._show_start_error(error)

    def _show_start_error(self, error):
        """Translates the key_handler.start() error and adds extra help on Linux"""
        tr = self.tr_manager
        err_title = tr("error_title")
        err_msg = tr(error)

        if error == "error_admin_required" and sys.platform.startswith('linux'):
            err_msg += "\n\n" + tr("error_admin_required_linux_hint")

        messagebox.showerror(err_title, err_msg)

        # NEW: Update the minimized icon if it is visible
        if self.is_minimized and self.minimized_window:
            # Get the new state directly from the handler
            new_state = self.key_handler.is_active()
            self.minimized_window.update_visuals(new_state)

    def _restore_window(self, center_pos=None):
        """Restores the window, ensuring it stays within screen bounds"""
        if self.minimized_window: 
            self.minimized_window.hide()
            
        if center_pos:
            # Unpack the target center
            cx, cy = center_pos
            
            # Get the current dimensions of the main window
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            
            # Fallback in case the window has not been rendered yet
            if w < 100: w = 650
            if h < 100: h = 550
            
            # Get the screen dimensions
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            
            # Calculate the ideal top-left corner (centered on the icon)
            new_x = int(cx - (w / 2))
            new_y = int(cy - (h / 2))
            
            # CLAMP TO KEEP IT ON SCREEN
            
            # X axis:
            # - Not less than 0 (Left edge)
            # - Not more than screen_w - w (Right edge)
            new_x = max(0, min(new_x, screen_w - w))
            
            # Y axis:
            # - Not less than 0 (Top edge)
            # - Not more than screen_h - h (Bottom edge)
            new_y = max(0, min(new_y, screen_h - h))
            
            # Move the window to the safe position
            self.root.geometry(f"+{new_x}+{new_y}")
            
        self.root.deiconify()
        self.is_minimized = False

    def _on_close(self):
        """Stops the script and exits the application."""
        if self.key_handler.is_active(): self.key_handler.stop()
        self.root.destroy()
        # Hard exit: with the exclusive keyboard grab (EVIOCGRAB) we do not
        # risk any thread/descriptor leaving the process hanging in the
        # background. The kernel releases the grab when the process dies.
        import os
        os._exit(0)

    def run(self):
        """Runs the Tk main event loop."""
        self.root.mainloop()
