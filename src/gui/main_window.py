"""
Ventana principal de la aplicación KeyForge - Diseño Tabulado
"""
import ttkbootstrap as ttk
from tkinter import messagebox
import sys, os
from ..config import ConfigManager
from ..core import KeyHandler, AppMonitor
from ..utils import WindowManager
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
        self.logger = get_logger()
        self.config_manager = ConfigManager()

        # Configuramos tema antes de crear ventana
        current_theme = self.config_manager.config.get("theme", "darkly")
        
        # 1. Crear ventana (pero oculta)
        self._create_window(current_theme) 
        
        # ### CAMBIO: Mostrar Splash Screen inmediatamente después de crear root
        # Pasamos el root para que el splash herede el tema
        self.splash = SplashScreen(
            self.root, 
            tr_dict=self.config_manager.tr,
            title="KeyForge", 
            version=CURRENT_VERSION
        )
        self.splash.update_step(5, self.config_manager.tr.get("splash_config", "Cargando configuración..."))

        self.app_monitor = AppMonitor()
        self.key_handler = KeyHandler(self.app_monitor)
        self.window_manager = WindowManager()

        self.is_minimized = False
        self.minimized_window = None
        self.drag_data = {"x": 0, "y": 0}
        self.is_restarting = False
        
        # 2. Configuraciones iniciales
        self.splash.update_step(20, self.config_manager.tr.get("splash_gui", "Inicializando componentes..."))
        self.key_handler.set_tk_root(self.root)

        self._create_ui_structure()
        self._load_initial_config()

        # 3. Programar la carga pesada y finalización del splash
        self.root.after(100, self._post_initialization)

    def _load_initial_config(self):
        """Carga solo lo visualmente esencial"""
        config = self.config_manager.config
        # Establecemos valores visuales rápidos
        self.app_focus_component.app_focus_var.set(config.get("enforce_app_focus", True))
        if config.get("target_app_name"):
            self.app_focus_component.set_app_name(config.get("target_app_name"))

    def _load_heavy_logic(self):
        """El resto de la configuración que requiere procesamiento"""
        config = self.config_manager.config
        
        # Configurar monitor
        self.app_monitor.set_enforce_focus(config.get("enforce_app_focus", True))
        self.app_monitor.set_target_app(config.get("target_app_name", ""))
        
        # Cargar reglas
        rules_data = config.get("rules", [])
        if rules_data:
            self.key_handler.load_rules(rules_data)
        self._refresh_rules_ui()
        
        # ESTA ES LA CLAVE: Escanear ventanas es lento, ahora se hace aquí
        self._refresh_windows_list()
        self._toggle_app_focus()

    def _create_window(self, theme_name):
        self.root = ttk.Window(themename=theme_name)
        self.root.overrideredirect(True)
        self.root.title("KeyForge")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.withdraw()

    def _post_initialization(self):
        """Tareas pesadas y cierre del splash"""
    
        if hasattr(self, 'splash'): 
            self.splash.update_step(40, self.config_manager.tr.get("splash_scan", "Escaneando sistema..."))
        self._finalize_window_layout()
    
        if hasattr(self, 'splash'): 
            self.splash.update_step(60, self.config_manager.tr.get("splash_rules", "Cargando reglas..."))
        self._load_heavy_logic()
    
        if hasattr(self, 'splash'): 
            self.splash.update_step(80, self.config_manager.tr.get("splash_monitors", "Iniciando monitores..."))
        self._init_monitoring()
    
        if hasattr(self, 'splash'): 
            self.splash.update_step(100, self.config_manager.tr.get("splash_done", "¡Listo!"))
    
        self.root.after(500, self._finish_loading)
    
    def _finish_loading(self):
        """Cierra splash y muestra ventana principal"""
        if hasattr(self, 'splash'):
            self.splash.close()
            del self.splash
        
        # Mostrar ventana principal
        self.root.deiconify() 
        # Asegurarse que esté encima
        self.root.lift()
        self.root.attributes('-topmost', True)

    def _finalize_window_layout(self):
        """Calcula el tamaño ideal basado en el contenido de las pestañas"""
        self.root.update_idletasks()
        
        # Obtenemos tamaño requerido
        req_w = self.root.winfo_reqwidth()
        req_h = self.root.winfo_reqheight()
        
        # Aseguramos un ancho mínimo para que no se vea muy estrecho
        final_w = max(req_w, 650) 
        # Aseguramos un alto mínimo
        final_h = max(req_h, 550)
        
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        
        x = int((screen_w / 2) - (final_w / 2))
        y = int((screen_h / 2) - (final_h / 2))
        
        self.root.geometry(f"{final_w}x{final_h}+{x}+{y}")

    def _create_ui_structure(self):
        tr = self.config_manager.tr
        
        # --- 1. HEADER (Solo Título y Arrastre) ---
        header = ttk.Frame(self.root, bootstyle="secondary")
        header.pack(fill="x", ipady=5)
        
        # Título (sin botones de ventana)
        from .. import __version__
        title = ttk.Label(header, text=f"🔧 KeyForge v{__version__}", font=("Segoe UI", 12, "bold"), bootstyle="inverse-secondary")
        title.pack(side="left", padx=15)

        # Arrastre (Vinculado al header y al título)
        for w in [header, title]:
            w.bind("<Button-1>", lambda e: self.window_manager.start_drag(e, self.root))
            w.bind("<B1-Motion>", lambda e: self.window_manager.drag(e, self.root))

        # --- 2. CUERPO PRINCIPAL (Pestañas) ---
        self.notebook = ttk.Notebook(self.root, bootstyle="primary")
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Pestaña 1: Dashboard
        self.tab_dashboard = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_dashboard, text=f" {tr.get('title', 'Dashboard')} ")
        
        # Pestaña 2: Reglas
        self.tab_rules = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_rules, text=f" {tr.get('rules_title', 'Rules')} ")
        
        # Pestaña 3: Accesibilidad
        self.tab_accessibility = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_accessibility, text=f" {tr.get('accessibility_title', 'Accessibility')} ")

        # --- CONTENIDO DASHBOARD ---
        self.status_component = StatusComponent(self.tab_dashboard, tr)
        
        ttk.Separator(self.tab_dashboard).pack(fill="x", pady=15)
        
        self.app_focus_component = AppFocusComponent(
            self.tab_dashboard, tr, 
            self._refresh_windows_list, self._toggle_app_focus, self._on_app_selected
        )
        
        ttk.Separator(self.tab_dashboard).pack(fill="x", pady=15)

        self.control_buttons = ControlButtonsComponent(
            self.tab_dashboard, 
            tr,
            on_toggle_callback=self._toggle_script, 
            on_save_callback=self._save_config,
            on_minimize_callback=self._minimize_custom,
            on_exit_callback=self._on_close
        )

        # --- CONTENIDO REGLAS ---
        self.rules_manager = RulesManagerComponent(
            self.tab_rules, tr,
            on_detect_key_callback=self._on_detect_key_request
        )
        
        self.rules_manager.on_add_rule = self._add_rule_logic
        self.rules_manager.on_edit_rule = self._edit_rule_logic
        self.rules_manager.on_delete_rule = self._delete_rule_logic
        
        # --- CONTENIDO ACCESIBILIDAD ---
        current_lang = self.config_manager.config.get("lang", "en")
        current_theme = self.config_manager.config.get("theme", "darkly")
        
        self.accessibility_component = AccessibilityComponent(
            self.tab_accessibility,
            tr,
            current_lang,
            current_theme,
            self._on_accessibility_change
        )

    # --- Lógica de Reglas ---
    
    def _add_rule_logic(self, rule_data):
        success, error = self.key_handler.add_rule(
            rule_data['key_to_replace'], rule_data['replacement_key'],
            rule_data['mode'], rule_data['enabled']
        )
        if success: self._refresh_rules_ui()
        else: messagebox.showerror("Error", error)

    def _edit_rule_logic(self, index, rule_data):
        # Lógica para actualizar la regla existente en el core
        success, error = self.key_handler.update_rule(
            index,
            rule_data['key_to_replace'], rule_data['replacement_key'],
            rule_data['mode'], rule_data['enabled']
        )
        if success: self._refresh_rules_ui()
        else: messagebox.showerror("Error", error)

    def _delete_rule_logic(self, index):
        if self.key_handler.remove_rule(index): self._refresh_rules_ui()

    def _refresh_rules_ui(self):
        self.rules_manager.load_rules(self.key_handler.get_rules())

    def _on_detect_key_request(self, callback):
        self.key_handler.listen_for_key(callback)

    # --- Core Logic & Config (Igual que antes) ---
    def _load_configuration(self):
        config = self.config_manager.config
        self.app_monitor.set_enforce_focus(config.get("enforce_app_focus", True))
        self.app_monitor.set_target_app(config.get("target_app_name", ""))
        
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
        """Guarda la configuración actual"""
        # 1. Obtener datos de los componentes VIGENTES
        app_name = self.app_focus_component.get_app_name()
        enforce_focus = self.app_focus_component.is_focus_enabled()
        
        # 2. Obtener las reglas directamente del manejador (Core)
        # Ya no usamos key_config_component ni mode_component
        rules_to_save = [rule.to_dict() for rule in self.key_handler.get_rules()]
        
        config_data = {
            "rules": rules_to_save,
            "enforce_app_focus": enforce_focus,
            "target_app_name": app_name if enforce_focus else ""
        }
        
        # 3. Guardar usando el ConfigManager
        if self.config_manager.save_config(config_data):
            from ..config import CONFIG_FILE
            
            # 4. Mensaje de éxito TRADUCIDO
            title = self.config_manager.tr.get("saved_title", "Configuration Saved")
            
            # Obtenemos el template traducido (ej: "Guardado en:\n{configfile}")
            msg_template = self.config_manager.tr.get("saved_msg", "Saved in:\n{configfile}")
            
            # Reemplazamos el placeholder con la ruta real
            msg = msg_template.replace("{configfile}", str(CONFIG_FILE))
            
            messagebox.showinfo(title, msg)

    def _add_rule_logic(self, rule_data):
        success, error = self.key_handler.add_rule(
            rule_data['key_to_replace'], rule_data['replacement_key'],
            rule_data['mode'], rule_data['enabled']
        )
        if success:
            self._refresh_rules_ui()
        else:
            # TRADUCIR TÍTULO Y MAPEAR ERROR
            err_title = self.config_manager.tr.get("error_title", "Error")
            # Traducir el mensaje de error que viene del backend (ver Paso 2)
            err_msg = self.config_manager.tr.get(error, error) 
            messagebox.showerror(err_title, err_msg)

    def _edit_rule_logic(self, index, rule_data):
        success, error = self.key_handler.update_rule(
            index,
            rule_data['key_to_replace'], rule_data['replacement_key'],
            rule_data['mode'], rule_data['enabled']
        )
        if success:
            self._refresh_rules_ui()
        else:
            # TRADUCIR TÍTULO Y MAPEAR ERROR
            err_title = self.config_manager.tr.get("error_title", "Error")
            err_msg = self.config_manager.tr.get(error, error)
            messagebox.showerror(err_title, err_msg)

    def _toggle_script(self):
        if self.key_handler.is_active():
            self.key_handler.stop()
            self.status_component.update_script_status(False)
            self.control_buttons.set_toggle_state(False)
            self.rules_manager.set_controls_state(True)
            self.app_focus_component.set_controls_state(True)
        else:
            if not self.key_handler.get_rules():
                messagebox.showwarning("KeyForge", "Add at least one rule first.")
                return
            
            self.app_monitor.set_enforce_focus(self.app_focus_component.is_focus_enabled())
            self.app_monitor.set_target_app(self.app_focus_component.get_app_name())
            
            success, error = self.key_handler.start()
            if success:
                self.status_component.update_script_status(True, len(self.key_handler.get_rules()))
                self.control_buttons.set_toggle_state(True)
                self.rules_manager.set_controls_state(False)
                self.app_focus_component.set_controls_state(False)
            else:
                messagebox.showerror("Error", error)

    def _init_monitoring(self):
        def on_app_change(active):
            self.status_component.update_app_status(
                not self.app_monitor.enforce_app_focus, active, self.app_monitor.target_app_name
            )
        if sys.platform == 'win32':
            if self.app_monitor.use_event_monitoring(on_app_change): return
        self._start_polling_monitoring()

    def _start_polling_monitoring(self):
        self.app_monitor.update_status()
        self.status_component.update_app_status(
            not self.app_monitor.enforce_app_focus, 
            self.app_monitor.target_app_is_active, 
            self.app_monitor.target_app_name
        )
        self._polling_id = self.root.after(500, self._start_polling_monitoring)

    # --- Accesibilidad ---
    
    def _on_accessibility_change(self, setting_type, value):
        """
        Callback cuando cambia alguna configuración de accesibilidad.
        Guarda automáticamente y reinicia la interfaz.
        """
        if hasattr(self, 'is_restarting') and self.is_restarting:
            return
        
        # Guardar el nuevo valor en la configuración
        config_update = {setting_type: value}
        
        # Preservar configuración existente
        config_update["rules"] = [rule.to_dict() for rule in self.key_handler.get_rules()]
        config_update["enforce_app_focus"] = self.app_focus_component.is_focus_enabled()
        config_update["target_app_name"] = self.app_focus_component.get_app_name()
        
        # Actualizar el valor que cambió
        if setting_type == "lang":
            config_update["theme"] = self.config_manager.config.get("theme", "darkly")
        else:  # theme
            config_update["lang"] = self.config_manager.config.get("lang", "en")
        
        # Guardar configuración
        if self.config_manager.save_config(config_update):
            # Reiniciar la aplicación para aplicar cambios
            self._restart_application()
    
    def _restart_application(self):
        """Reinicia el proceso de la aplicación completamente"""
        if self.is_restarting:
            return

        self.is_restarting = True
        self.logger.info("Iniciando secuencia de reinicio...") # Log informativo

        # 1. Guardar estado y detener hilos
        try:
            if self.key_handler.is_active():
                self.key_handler.stop()
            self._stop_all_monitoring()
        except Exception as e:
            # CAMBIO: Usar logger.error en lugar de print
            self.logger.error(f"Error limpiando antes de reiniciar: {e}")

        # 2. Destruir la ventana actual
        try:
            self.root.destroy()
        except:
            pass

        # 3. REINICIO ROBUSTO DEL PROCESO
        # CAMBIO: Usar logger.info en lugar de print
        self.logger.info("Ejecutando reinicio del proceso...")
        
        if getattr(sys, 'frozen', False):
             # Si es un ejecutable (PyInstaller)
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            # Si es un script de Python (.py)
            os.execl(sys.executable, sys.executable, *sys.argv)

    def _stop_all_monitoring(self):
        """Detiene todos los sistemas de monitoreo activos"""
        try:
            # Detener polling si existe
            if hasattr(self, '_polling_id'):
                self.root.after_cancel(self._polling_id)
                self._polling_id = None
        except:
            pass
    
        try:
            # Detener event monitoring
            if hasattr(self.app_monitor, 'stop_event_monitoring'):
                self.app_monitor.stop_event_monitoring()
        except:
            pass

    # --- Window Utilities ---
    def _refresh_windows_list(self):
        self.app_focus_component.update_app_list(self.app_monitor.get_all_windows())

    def _toggle_app_focus(self):
        enforce = self.app_focus_component.is_focus_enabled()
        self.app_monitor.set_enforce_focus(enforce)
        if enforce:
            self.app_focus_component.app_combo.config(state="readonly")
            self.app_focus_component.btn_refresh.config(state="normal")
        else:
            self.app_focus_component.app_combo.config(state="disabled")
            self.app_focus_component.btn_refresh.config(state="disabled")
        self.app_monitor.update_status()

    def _on_app_selected(self):
        if self.app_focus_component.is_focus_enabled():
            self.app_monitor.set_target_app(self.app_focus_component.get_app_name())
            self.app_monitor.update_status()

    def _start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + event.x - self.drag_data["x"]
        y = self.root.winfo_y() + event.y - self.drag_data["y"]
        self.root.geometry(f"+{x}+{y}")

    def _minimize_custom(self):
        """Minimiza la ventana a un icono flotante conservando la posición visual"""
        if self.is_minimized:
            return
        
        # CALCULAR CENTRO ACTUAL DE LA VENTANA PRINCIPAL
        # Hacemos esto ANTES de withdraw() para obtener las coordenadas correctas
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
        
        # PASAR EL CENTRO CALCULADO A SHOW()
        self.minimized_window.show(
            is_active=is_script_active, 
            center_pos=(center_x, center_y)
        )
        
        self.is_minimized = True

    def _toggle_script(self):
        # Lógica original para detener
        if self.key_handler.is_active():
            self.key_handler.stop()
            self.status_component.update_script_status(False)
            self.control_buttons.set_toggle_state(False)
            self.rules_manager.set_controls_state(True)
            self.app_focus_component.set_controls_state(True)
        else:
            # Lógica original para iniciar
            if not self.key_handler.get_rules():
                # Si está minimizado y da error, mostramos un popup simple porque la ventana principal no se ve
                if self.is_minimized:
                    messagebox.showwarning("KeyForge", "Add at least one rule first.")
                else:
                    messagebox.showwarning("KeyForge", "Add at least one rule first.")
                return
            
            self.app_monitor.set_enforce_focus(self.app_focus_component.is_focus_enabled())
            self.app_monitor.set_target_app(self.app_focus_component.get_app_name())
            
            success, error = self.key_handler.start()
            if success:
                self.status_component.update_script_status(True, len(self.key_handler.get_rules()))
                self.control_buttons.set_toggle_state(True)
                self.rules_manager.set_controls_state(False)
                self.app_focus_component.set_controls_state(False)
            else:
                messagebox.showerror("Error", error)

        # NUEVO: Actualizar el icono minimizado si está visible
        if self.is_minimized and self.minimized_window:
            # Obtenemos el nuevo estado directamente del handler
            new_state = self.key_handler.is_active()
            self.minimized_window.update_visuals(new_state)

    def _restore_window(self, center_pos=None):
        """Restaura la ventana, opcionalmente centrada en una posición"""
        if self.minimized_window: 
            self.minimized_window.hide()
            
        if center_pos:
            # Desempaquetar el centro objetivo
            cx, cy = center_pos
            
            # Obtener dimensiones actuales de la ventana principal
            # Usamos winfo_width/height para exactitud, o fallback a lo solicitado
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            
            # Si la ventana nunca se mostró, winfo puede ser 1x1. 
            # Aseguramos dimensiones mínimas por si acaso.
            if w < 100: w = 650
            if h < 100: h = 550
            
            # Calcular nueva esquina superior izquierda (x, y)
            new_x = int(cx - (w / 2))
            new_y = int(cy - (h / 2))
            
            # Mover la ventana ANTES de mostrarla
            self.root.geometry(f"+{new_x}+{new_y}")
            
        self.root.deiconify()
        self.is_minimized = False

    def _on_close(self):
        if self.key_handler.is_active(): self.key_handler.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()