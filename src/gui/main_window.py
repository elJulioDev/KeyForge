"""
Ventana principal de la aplicación KeyForge
"""
import ttkbootstrap as ttk
from tkinter import messagebox

from ..config import ConfigManager
from ..core import KeyHandler, AppMonitor
from ..utils import WindowManager
from .components import (
    StatusComponent,
    KeyConfigComponent,
    ModeComponent,
    AppFocusComponent,
    ControlButtonsComponent,
    CommonKeysWindow
)
from .minimized_window import MinimizedWindow


class KeyForgeApp:
    """Aplicación principal de KeyForge"""
    
    def __init__(self):
        # Configuración
        self.config_manager = ConfigManager()
        
        # Core
        self.app_monitor = AppMonitor()
        self.key_handler = KeyHandler(self.app_monitor)
        
        # Utilidades
        self.window_manager = WindowManager()
        
        # Estado
        self.is_minimized = False
        self.minimized_window = None
        
        # Variables para arrastre de ventana
        self.window_drag_x = 0
        self.window_drag_y = 0
        
        # GUI
        self._create_window()
        self._create_components()
        self._load_configuration()
        self._start_app_monitoring()
    
    def _create_window(self):
        """Crea y configura la ventana principal"""
        self.root = ttk.Window(themename="darkly")
        self.root.overrideredirect(True)
        self.root.title("KeyForge")
        self.root.resizable(False, False)
        
        # Dimensiones y posición EXACTAS del original
        window_width = 750
        window_height = 850
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        pos_x = int(screen_width / 2 - window_width / 2)
        pos_y = int(screen_height / 2 - window_height / 2)
        
        self.root.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_components(self):
        """Crea todos los componentes de la GUI EN EL ORDEN EXACTO DEL ORIGINAL"""
        tr = self.config_manager.tr
        
        # ------- SECCIÓN ENCABEZADO COMPACTO (ÁREA DE ARRASTRE) --------
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=20, pady=(12, 8))
        
        title_label = ttk.Label(
            header_frame,
            text="KeyForge",
            font=("-size", 16, "-weight", "bold")
        )
        title_label.pack()
        
        # Hacer el encabezado arrastrable
        header_frame.bind("<Button-1>", self._start_window_drag)
        header_frame.bind("<B1-Motion>", self._drag_window)
        title_label.bind("<Button-1>", self._start_window_drag)
        title_label.bind("<B1-Motion>", self._drag_window)

        # Separador delgado
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=20, pady=8)
        
        # ---------- SECCIÓN ESTADO COMPACTO -----------
        self.status_component = StatusComponent(self.root, tr)
        
        # -------------- SECCIÓN APLICACIÓN OBJETIVO (ARRIBA) -------------
        self.app_focus_component = AppFocusComponent(
            self.root,
            tr,
            self._refresh_windows_list,
            self._toggle_app_focus,
            self._on_app_selected
        )
        
        # ---------- SECCIÓN CONFIGURACIÓN DE TECLAS --------------
        self.key_config_component = KeyConfigComponent(
            self.root,
            tr,
            self._on_detect_key,
            self._show_common_keys
        )
        
        # ------------ SECCIÓN MODO DE OPERACIÓN ---------------
        self.mode_component = ModeComponent(self.root, tr)
        
        
        # ----------- SECCIÓN CONTROLES PRINCIPALES ------------
        self.control_buttons = ControlButtonsComponent(
            self.root,
            tr,
            self._toggle_script,
            self._save_config,
            self._minimize_custom,
            self._on_close
        )
        
        # Separador delgado
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=20, pady=8)
        
        # ------- FOOTER VISIBLE -------------
        self._create_footer()
    
    def _create_footer(self):
        """Crea el footer con información"""
        footer_frame = ttk.Frame(self.root)
        footer_frame.pack(fill="x", padx=20, pady=(0, 12))
        
        from ..config import CONFIG_FILE
        from .. import __version__
        
        config_info = ttk.Label(
            footer_frame,
            text=f"📁 Config: {CONFIG_FILE.name}",
            font=("-size", 8),
            bootstyle="secondary"
        )
        config_info.pack()
        
        version_label = ttk.Label(
            footer_frame,
            text=f"v{__version__} | KeyForge",
            font=("-size", 8),
            bootstyle="secondary"
        )
        version_label.pack(pady=(2, 0))
    
    def _start_window_drag(self, event):
        """Inicia el arrastre de la ventana principal"""
        self.window_drag_x = event.x
        self.window_drag_y = event.y
    
    def _drag_window(self, event):
        """Arrastra la ventana principal"""
        x = self.root.winfo_x() + event.x - self.window_drag_x
        y = self.root.winfo_y() + event.y - self.window_drag_y
        self.root.geometry(f"+{x}+{y}")
    
    def _load_configuration(self):
        """Carga la configuración guardada"""
        config = self.config_manager.config
        
        # Aplicar configuración al monitor de apps
        self.app_monitor.set_enforce_focus(config.get("enforce_app_focus", True))
        self.app_monitor.set_target_app(config.get("target_app_name", ""))
        
        # Aplicar configuración al manejador de teclas
        self.key_handler.set_keys(
            config.get("key_to_replace", "alt"),
            config.get("replacement_key", "shift")
        )
        self.key_handler.set_mode(config.get("mode", "mantener"))
        
        # Actualizar componentes visuales
        self.key_config_component.replace_key_var.set(config.get("key_to_replace", "alt"))
        self.key_config_component.replacement_key_var.set(config.get("replacement_key", "shift"))
        self.mode_component.mode_var.set(config.get("mode", "mantener"))
        self.app_focus_component.app_focus_var.set(config.get("enforce_app_focus", True))
        
        # Cargar app guardada
        saved_app = config.get("target_app_name", "")
        if saved_app and self.app_focus_component.is_focus_enabled():
            self.app_focus_component.set_app_name(saved_app)
        
        # Actualizar lista de ventanas
        self._refresh_windows_list()
        self._toggle_app_focus()
    
    def _save_config(self):
        """Guarda la configuración actual"""
        keys = self.key_config_component.get_keys()
        mode = self.mode_component.get_mode()
        app_name = self.app_focus_component.get_app_name()
        enforce_focus = self.app_focus_component.is_focus_enabled()
    
        config_data = {
            "mode": mode,
            "key_to_replace": keys["replace"],
            "replacement_key": keys["replacement"],
            "enforce_app_focus": enforce_focus,
            "target_app_name": app_name if enforce_focus else ""
        }
    
        if self.config_manager.save_config(config_data):
            from ..config import CONFIG_FILE
        
            # Obtener el mensaje con el placeholder correcto
            message = self.config_manager.tr.get(
                "saved_msg", 
                "Configuración guardada exitosamente en:\n{configfile}"
            )
        
            # Reemplazar {configfile} con la ruta real
            message = message.replace("{configfile}", str(CONFIG_FILE))
        
            messagebox.showinfo(
                self.config_manager.tr.get("saved_title", "Configuración Guardada"),
                message
            )
    
    def _toggle_script(self):
        """Activa o desactiva el script"""
        if self.key_handler.is_active():
            # Detener el script
            self.key_handler.stop()
            self.status_component.update_script_status(False)
            self.control_buttons.set_toggle_state(False)
            self._enable_controls(True)
        else:
            # Iniciar el script
            keys = self.key_config_component.get_keys()
            mode = self.mode_component.get_mode()
            
            self.key_handler.set_keys(keys["replace"], keys["replacement"])
            self.key_handler.set_mode(mode)
            
            # Actualizar configuración del monitor
            self.app_monitor.set_enforce_focus(self.app_focus_component.is_focus_enabled())
            self.app_monitor.set_target_app(self.app_focus_component.get_app_name())
            
            self.key_handler.start()
            
            mode_text = self.config_manager.tr.get("hold", "Mantener") if mode == "mantener" else self.config_manager.tr.get("toggle", "Intercalar")
            
            self.status_component.update_script_status(True, {
                "src": keys["replace"],
                "dst": keys["replacement"],
                "mode": mode_text
            })
            self.control_buttons.set_toggle_state(True)
            self._enable_controls(False)
    
    def _enable_controls(self, enabled):
        """Habilita o deshabilita los controles de configuración"""
        self.key_config_component.set_controls_state(enabled)
        self.mode_component.set_controls_state(enabled)
        self.app_focus_component.set_controls_state(enabled)
    
    def _on_detect_key(self, target_var, status_label):
        """Detecta una tecla presionada"""
        self.key_handler.listen_for_key(lambda key, error: self._key_detected(key, error, target_var, status_label))
        status_label.config(text=self.config_manager.tr.get("press_key_label", "Presiona una tecla..."))
    
    def _key_detected(self, key, error, target_var, status_label):
        """Callback cuando se detecta una tecla"""
        if error:
            status_label.config(text=f"❌ Error: {error}")
        elif key:
            target_var.set(key)
            status_label.config(text=f"✅ {key}")
            
            # Restaurar texto original después de 2 segundos
            self.root.after(2000, lambda: status_label.config(text=""))
    
    def _show_common_keys(self):
        """Muestra la ventana de teclas comunes"""
        CommonKeysWindow(self.root, self.config_manager.tr)
    
    def _refresh_windows_list(self):
        """Actualiza la lista de ventanas abiertas"""
        windows = self.app_monitor.get_all_windows()
        self.app_focus_component.update_app_list(windows)
    
    def _toggle_app_focus(self):
        """Alterna el modo de enfoque de aplicación"""
        enforce = self.app_focus_component.is_focus_enabled()
        self.app_monitor.set_enforce_focus(enforce)
        
        if enforce:
            app_name = self.app_focus_component.get_app_name()
            self.app_monitor.set_target_app(app_name)
            self.app_focus_component.app_combo.config(state="readonly")
            self.app_focus_component.btn_refresh.config(state="normal")
        else:
            self.app_focus_component.app_combo.config(state="disabled")
            self.app_focus_component.btn_refresh.config(state="disabled")
        
        self._update_app_status()
    
    def _on_app_selected(self):
        """Callback cuando se selecciona una aplicación"""
        if self.app_focus_component.is_focus_enabled():
            app_name = self.app_focus_component.get_app_name()
            self.app_monitor.set_target_app(app_name)
            self._update_app_status()
    
    def _start_app_monitoring(self):
        """Inicia el monitoreo automático de la aplicación"""
        self._update_app_status()
    
    def _update_app_status(self):
        """Actualiza el estado de la aplicación (llamado recursivamente)"""
        is_global = not self.app_monitor.enforce_app_focus
        is_active = self.app_monitor.update_status()
        app_name = self.app_monitor.target_app_name
        
        self.status_component.update_app_status(is_global, is_active, app_name)
        
        # Llamar de nuevo en 500ms
        self.root.after(500, self._update_app_status)
    
    def _minimize_custom(self):
        """Minimiza la ventana a un icono flotante"""
        if self.is_minimized:
            return
        
        self.root.withdraw()
        self.minimized_window = MinimizedWindow(self.root, self._restore_window)
        self.minimized_window.show()
        self.is_minimized = True
    
    def _restore_window(self):
        """Restaura la ventana desde el estado minimizado"""
        if self.minimized_window:
            self.minimized_window.hide()
            self.minimized_window = None
        
        self.root.deiconify()
        self.root.attributes('-topmost', True)
        self.is_minimized = False
    
    def _on_close(self):
        """Maneja el cierre de la aplicación"""
        if self.key_handler.is_active():
            self.key_handler.stop()
        self.root.destroy()
    
    def run(self):
        """Inicia el loop principal de la aplicación"""
        self.root.mainloop()
