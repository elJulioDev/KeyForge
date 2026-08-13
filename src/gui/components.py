"""
Componentes individuales de la interfaz gráfica
"""
import ttkbootstrap as ttk
from tkinter import StringVar, BooleanVar, messagebox
from ..utils import WindowManager
from ..utils.icons import get_icon


class StatusComponent:
    """Componente que muestra el estado del script y la aplicación"""
    
    def __init__(self, parent, tr_manager):
        self.tr_manager = tr_manager
        self.tr = tr_manager
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Estado actual para re-aplicar en hot-reload
        self._is_active = False
        self._rule_count = 0
        self._is_global = True
        self._is_detected = False
        self._app_name = ""
        
        # Label de estado principal
        self.status_label = ttk.Label(
            self.frame,
            text=self.tr("status_stopped"),
            bootstyle="danger",
            font=("-size", 11, "-weight", "bold")
        )
        self.status_label.pack()
        
        # Label de estado de aplicación
        self.app_status_label = ttk.Label(
            self.frame,
            text=self.tr("waiting_config"),
            bootstyle="info",
            font=("-size", 8)
        )
        self.app_status_label.pack(pady=(3, 0))
    
    def update_script_status(self, is_active, rule_count=0):
        """Actualiza el estado del script"""
        self._is_active = is_active
        self._rule_count = rule_count
        
        if is_active:
            text = f"{self.tr('active_rules')}: {rule_count} {self.tr('rule_label')}"
            self.status_label.config(text=text, bootstyle="success")
        else:
            self.status_label.config(
                text=self.tr("status_stopped"),
                bootstyle="danger"
            )
    
    def update_app_status(self, is_global, is_detected, app_name=""):
        """Actualiza el estado de detección de la aplicación"""
        self._is_global = is_global
        self._is_detected = is_detected
        self._app_name = app_name
        
        if is_global:
            self.app_status_label.config(
                text=self.tr("global_mode"),
                bootstyle="info"
            )
        elif is_detected:
            self.app_status_label.config(
                text=self.tr("app_detected", app=app_name),
                bootstyle="success"
            )
        else:
            self.app_status_label.config(
                text=self.tr("waiting_app", app=app_name),
                bootstyle="info"
            )
    
    def update_translations(self):
        """Re-aplica traducciones con estado actual"""
        self.update_script_status(self._is_active, self._rule_count)
        self.update_app_status(self._is_global, self._is_detected, self._app_name)


class AppFocusComponent:
    """Componente de selección de aplicación específica"""
    
    def __init__(self, parent, tr_manager, on_refresh_callback, on_toggle_callback, on_selected_callback):
        self.tr_manager = tr_manager
        self.tr = tr_manager
        self.on_refresh = on_refresh_callback
        self.on_toggle = on_toggle_callback
        self.on_selected = on_selected_callback
        
        self.app_focus_var = BooleanVar(value=True)
        
        # Frame principal con título (LabelFrame)
        self.frame = ttk.Labelframe(
            parent,
            text=self.tr("target_app_title"),
            padding=12
        )
        self.frame.pack(padx=20, pady=(0, 10), fill="x")
        
        # Checkbox de enfoque
        self.check_app_focus = ttk.Checkbutton(
            self.frame,
            text=self.tr("focus_checkbox"),
            variable=self.app_focus_var,
            command=on_toggle_callback,
            bootstyle="round-toggle"
        )
        self.check_app_focus.pack(anchor="w", pady=(0, 8))
        
        # Selector de aplicación
        self._create_app_selector()
        
        # Info reducida
        self.info_label = ttk.Label(
            self.frame,
            text=self.tr("focus_info"),
            font=("-size", 8),
            bootstyle="secondary"
        )
        self.info_label.pack(pady=(6, 0))
    
    def _create_app_selector(self):
        """Crea el selector de aplicación"""
        app_select_container = ttk.Frame(self.frame)
        app_select_container.pack(fill="x")
        
        ttk.Label(
            app_select_container,
            text=self.tr("program_label"),
            font=("-size", 9, "-weight", "bold")
        ).grid(row=0, column=0, sticky="w", pady=4)
        
        self.app_combo = ttk.Combobox(
            app_select_container,
            state="readonly",
            width=40
        )
        self.app_combo.grid(row=0, column=1, padx=(8, 4), pady=4, sticky="ew")
        self.app_combo.bind("<<ComboboxSelected>>", lambda e: self.on_selected())
        
        icon_refresh = get_icon("refresh-cw", 18, ttk.Style().colors.info)
        self.btn_refresh = ttk.Button(
            app_select_container,
            image=icon_refresh,
            command=self.on_refresh,
            bootstyle="info-outline",
            width=4
        )
        self.btn_refresh.image = icon_refresh
        self.btn_refresh.grid(row=0, column=2, pady=4)
        
        app_select_container.columnconfigure(1, weight=1)
    
    def set_controls_state(self, enabled):
        """Habilita o deshabilita los controles"""
        self.check_app_focus.config(state="normal" if enabled else "disabled")
        
        if enabled and self.app_focus_var.get():
            self.app_combo.config(state="readonly")
            self.btn_refresh.config(state="normal")
        else:
            self.app_combo.config(state="disabled")
            self.btn_refresh.config(state="disabled")
    
    def get_app_name(self):
        """Retorna el nombre de la aplicación seleccionada"""
        return self.app_combo.get() if self.app_focus_var.get() else ""
    
    def set_app_name(self, app_name):
        """Establece el nombre de la aplicación"""
        try:
            self.app_combo.set(app_name)
        except:
            pass
    
    def update_app_list(self, apps):
        """Actualiza la lista de aplicaciones"""
        self.app_combo['values'] = apps
        if apps and not self.app_combo.get():
            self.app_combo.set(apps[0])
    
    def is_focus_enabled(self):
        """Retorna si el enfoque está habilitado"""
        return self.app_focus_var.get()
    
    def update_translations(self):
        """Actualiza textos estáticos"""
        self.frame.config(text=self.tr("target_app_title"))
        self.check_app_focus.config(text=self.tr("focus_checkbox"))
        self.info_label.config(text=self.tr("focus_info"))


class ControlButtonsComponent:
    """Componente de botones de control principal"""
    
    def __init__(self, parent, tr_manager, on_toggle_callback, on_save_callback, 
                 on_minimize_callback, on_exit_callback):
        self.tr_manager = tr_manager
        self.tr = tr_manager
        
        # Estado del script para re-aplicar en hot-reload
        self._is_active = False
        
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.icon_play = get_icon("play", 18, "#FFFFFF")
        self.icon_pause = get_icon("pause", 18, "#FFFFFF")
        icon_save = get_icon("save", 18, "#FFFFFF")
        icon_minimize = get_icon("minus", 18, "#FFFFFF")
        icon_exit = get_icon("x", 18, "#FFFFFF")

        # Botón principal de activar/desactivar (Grande)
        self.toggle_btn = ttk.Button(
            self.frame,
            text=self.tr("activate_script_btn"),
            image=self.icon_play, compound="left",
            command=on_toggle_callback,
            bootstyle="success",
            cursor="hand2"
        )
        self.toggle_btn.pack(fill="x", pady=(0, 8), ipady=8)
        
        # Contenedor para los botones inferiores
        secondary_btns = ttk.Frame(self.frame)
        secondary_btns.pack(fill="x")
        
        # Botón Guardar (Izquierda)
        self.btn_save = ttk.Button(
            secondary_btns,
            text=self.tr("save_btn"),
            image=icon_save, compound="left",
            command=on_save_callback,
            bootstyle="info"
        )
        self.btn_save.image = icon_save
        self.btn_save.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        # Botón Minimizar (Centro)
        self.btn_minimize = ttk.Button(
            secondary_btns,
            text=self.tr("minimize_btn"),
            image=icon_minimize, compound="left",
            command=on_minimize_callback,
            bootstyle="secondary"
        )
        self.btn_minimize.image = icon_minimize
        self.btn_minimize.pack(side="left", fill="x", expand=True, padx=(4, 4))
        
        # Botón Salir (Derecha)
        self.btn_exit = ttk.Button(
            secondary_btns,
            text=self.tr("exit_btn"),
            image=icon_exit, compound="left",
            command=on_exit_callback,
            bootstyle="danger"
        )
        self.btn_exit.image = icon_exit
        self.btn_exit.pack(side="left", fill="x", expand=True, padx=(4, 0))
    
    def set_toggle_state(self, is_active):
        """Actualiza el estado del botón de activación"""
        self._is_active = is_active
        
        if is_active:
            self.toggle_btn.config(
                text=self.tr("stop_script_btn"),
                image=self.icon_pause,
                bootstyle="warning"
            )
        else:
            self.toggle_btn.config(
                text=self.tr("activate_script_btn"),
                image=self.icon_play,
                bootstyle="success"
            )
    
    def update_translations(self):
        """Actualiza textos de botones"""
        # Re-aplicar toggle con estado actual
        self.set_toggle_state(self._is_active)
        # Botones estáticos
        self.btn_save.config(text=self.tr("save_btn"))
        self.btn_minimize.config(text=self.tr("minimize_btn"))
        self.btn_exit.config(text=self.tr("exit_btn"))


class CommonKeysWindow:
    """Ventana que muestra las teclas comunes"""
    
    def __init__(self, parent, tr_manager):
        self.tr_manager = tr_manager
        self.tr = tr_manager
        self.window_manager = WindowManager()
        
        self.window = ttk.Toplevel(parent)
        self.window.title(self.tr("common_keys_title"))
        
        self.window.resizable(False, False)
        self.window.transient(parent)
        
        self._create_content()
        
        self.window_manager.center_and_resize(self.window)
        self.window_manager.elevate(self.window, parent)
        self.window_manager.safe_grab_set(self.window)

    def _create_content(self):
        main_container = ttk.Frame(self.window, padding=15)
        main_container.pack(fill="both", expand=True)
        
        title = ttk.Label(main_container, text=self.tr("common_keys_desc"), font=("-size", 13, "-weight", "bold"))
        title.pack(pady=(0, 15))
        
        text_frame = ttk.Frame(main_container)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        text_widget = ttk.Text(text_frame, yscrollcommand=scrollbar.set, wrap="word", font=("-family", "Consolas", "-size", 9))
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)
        
        text_widget.insert("1.0", self._get_common_keys_text().strip())
        text_widget.config(state="disabled")
        
        ttk.Button(main_container, text=self.tr("close_btn"), command=self.window.destroy, bootstyle="secondary").pack(pady=(10, 0), fill="x")
    
    def _get_common_keys_text(self):
        """Retorna el texto con las teclas comunes"""
        return f"""{self.tr("keys_letters")}: a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z

{self.tr("keys_numbers")}: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9

{self.tr("keys_function")}: f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12

{self.tr("keys_modifiers")}: shift, ctrl, alt, caps lock, tab, esc

{self.tr("keys_navigation")}: up, down, left, right, home, end, page up, page down

{self.tr("keys_special")}: space, enter, backspace, delete, insert

{self.tr("keys_numpad")}: num 0, num 1, num 2, num 3, num 4, num 5, num 6, num 7, num 8, num 9
   num lock, num +, num *, num -, num /, num enter, num .

{self.tr("keys_punctuation")}: . (period), , (comma), ; (semicolon), ' (apostrophe)
   [ (left bracket), ] (right bracket), \\ (backslash)
   - (minus), = (equal), ` (grave)

{self.tr("keys_note")}: {self.tr("keys_note_text")}
"""
