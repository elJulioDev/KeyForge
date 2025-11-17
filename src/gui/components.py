"""
Componentes individuales de la interfaz gráfica
"""
import ttkbootstrap as ttk
from tkinter import StringVar, BooleanVar, messagebox


class StatusComponent:
    """Componente que muestra el estado del script y la aplicación"""
    
    def __init__(self, parent, tr):
        self.tr = tr
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Label de estado principal
        self.status_label = ttk.Label(
            self.frame,
            text=self.tr.get("status_stopped", "Detenido"),
            bootstyle="danger",
            font=("-size", 11, "-weight", "bold")
        )
        self.status_label.pack()
        
        # Label de estado de aplicación
        self.app_status_label = ttk.Label(
            self.frame,
            text=self.tr.get("waiting_config", "Esperando configuración..."),
            bootstyle="info",
            font=("-size", 8)
        )
        self.app_status_label.pack(pady=(3, 0))
    
    def update_script_status(self, is_active, key_info=None):
        """Actualiza el estado del script (activo/detenido)"""
        if is_active:
            text = self.tr.get("status_running", "Activo").format(
                src=key_info['src'],
                dst=key_info['dst'],
                mode=key_info['mode']
            ) if key_info else self.tr.get("status_running", "Activo")
            self.status_label.config(text=text, bootstyle="success")
        else:
            self.status_label.config(
                text=self.tr.get("status_stopped", "Detenido"),
                bootstyle="danger"
            )
    
    def update_app_status(self, is_global, is_detected, app_name=""):
        """Actualiza el estado de detección de la aplicación"""
        if is_global:
            self.app_status_label.config(
                text=self.tr.get("global_mode", "Modo Global - Todos los programas"),
                bootstyle="info"
            )
        elif is_detected:
            self.app_status_label.config(
                text=self.tr.get("app_detected", "App Detectada").format(app=app_name),
                bootstyle="success"
            )
        else:
            self.app_status_label.config(
                text=self.tr.get("waiting_app", "Esperando app...").format(app=app_name),
                bootstyle="info"
            )


class KeyConfigComponent:
    """Componente de configuración de teclas"""
    
    def __init__(self, parent, tr, on_detect_callback, on_show_keys_callback):
        self.tr = tr
        self.on_detect = on_detect_callback
        self.on_show_keys = on_show_keys_callback
        
        # Variables
        self.replace_key_var = StringVar(value="alt")
        self.replacement_key_var = StringVar(value="shift")
        
        # Frame principal
        self.frame = ttk.LabelFrame(
            parent,
            text=self.tr.get("key_config_title", "Configuración de Teclas"),
            padding=12
        )
        self.frame.pack(padx=20, pady=(0, 10), fill="x")
        
        # Grid para las teclas
        self._create_key_grid()
        
        # Botón de ayuda
        self.btn_show_keys = ttk.Button(
            self.frame,
            text=self.tr.get("show_keys_btn", "Ver teclas comunes"),
            command=on_show_keys_callback,
            bootstyle="secondary-outline"
        )
        self.btn_show_keys.pack(fill="x", pady=(10, 0))
    
    def _create_key_grid(self):
        """Crea el grid de configuración de teclas"""
        keys_grid = ttk.Frame(self.frame)
        keys_grid.pack(fill="x")
        
        # Tecla a reemplazar
        ttk.Label(
            keys_grid,
            text=self.tr.get("replace_label", "Reemplazar:"),
            font=("-size", 9, "-weight", "bold")
        ).grid(row=0, column=0, sticky="w", pady=6)
        
        self.replace_entry = ttk.Entry(
            keys_grid,
            textvariable=self.replace_key_var,
            width=16,
            font=("-size", 9)
        )
        self.replace_entry.grid(row=0, column=1, padx=8, pady=6)
        
        self.replace_status = ttk.Label(keys_grid, text="", width=10)
        self.replace_status.grid(row=0, column=2, padx=4, pady=6)
        
        self.btn_detect_replace = ttk.Button(
            keys_grid,
            text=self.tr.get("detect_btn", "Detectar"),
            command=lambda: self.on_detect(self.replace_key_var, self.replace_status),
            bootstyle="info-outline",
            width=10
        )
        self.btn_detect_replace.grid(row=0, column=3, pady=6)
        
        # Tecla de reemplazo
        ttk.Label(
            keys_grid,
            text=self.tr.get("with_label", "Con:"),
            font=("-size", 9, "-weight", "bold")
        ).grid(row=1, column=0, sticky="w", pady=6)
        
        self.replacement_entry = ttk.Entry(
            keys_grid,
            textvariable=self.replacement_key_var,
            width=16,
            font=("-size", 9)
        )
        self.replacement_entry.grid(row=1, column=1, padx=8, pady=6)
        
        self.replacement_status = ttk.Label(keys_grid, text="", width=10)
        self.replacement_status.grid(row=1, column=2, padx=4, pady=6)
        
        self.btn_detect_replacement = ttk.Button(
            keys_grid,
            text=self.tr.get("detect_btn", "Detectar"),
            command=lambda: self.on_detect(self.replacement_key_var, self.replacement_status),
            bootstyle="info-outline",
            width=10
        )
        self.btn_detect_replacement.grid(row=1, column=3, pady=6)
    
    def set_controls_state(self, enabled):
        """Habilita o deshabilita los controles"""
        state = "normal" if enabled else "disabled"
        self.btn_detect_replace.config(state=state)
        self.btn_detect_replacement.config(state=state)
        self.btn_show_keys.config(state=state)
    
    def get_keys(self):
        """Retorna las teclas configuradas"""
        return {
            "replace": self.replace_key_var.get(),
            "replacement": self.replacement_key_var.get()
        }


class ModeComponent:
    """Componente de selección de modo de operación"""
    
    def __init__(self, parent, tr):
        self.tr = tr
        self.mode_var = StringVar(value="mantener")
        
        self.frame = ttk.LabelFrame(
            parent,
            text=self.tr.get("mode_title", "Modo de Operación"),
            padding=12
        )
        self.frame.pack(padx=20, pady=(0, 10), fill="x")
        
        # Radio buttons
        self.radio_hold = ttk.Radiobutton(
            self.frame,
            text=self.tr.get("hold_mode", "Mantener presionada"),
            variable=self.mode_var,
            value="mantener"
        )
        self.radio_hold.pack(anchor="w", pady=4)
        
        self.radio_toggle = ttk.Radiobutton(
            self.frame,
            text=self.tr.get("toggle_mode", "Intercalar on/off"),
            variable=self.mode_var,
            value="intercalar"
        )
        self.radio_toggle.pack(anchor="w", pady=4)
    
    def set_controls_state(self, enabled):
        """Habilita o deshabilita los controles"""
        state = "normal" if enabled else "disabled"
        self.radio_hold.config(state=state)
        self.radio_toggle.config(state=state)
    
    def get_mode(self):
        """Retorna el modo seleccionado"""
        return self.mode_var.get()


class AppFocusComponent:
    """Componente de selección de aplicación específica"""
    
    def __init__(self, parent, tr, on_refresh_callback, on_toggle_callback, on_selected_callback):
        self.tr = tr
        self.on_refresh = on_refresh_callback
        self.on_toggle = on_toggle_callback
        self.on_selected = on_selected_callback
        
        self.app_focus_var = BooleanVar(value=True)
        
        # Frame principal con título (LabelFrame)
        self.frame = ttk.LabelFrame(
            parent,
            text=tr.get("target_app_title", "Aplicación Objetivo"),
            padding=12
        )
        self.frame.pack(padx=20, pady=(0, 10), fill="x")
        
        # Checkbox de enfoque
        self.check_app_focus = ttk.Checkbutton(
            self.frame,
            text=self.tr.get("focus_checkbox", "Enfoque en aplicación específica"),
            variable=self.app_focus_var,
            command=on_toggle_callback,
            bootstyle="round-toggle"
        )
        self.check_app_focus.pack(anchor="w", pady=(0, 8))
        
        # Selector de aplicación
        self._create_app_selector()
        
        # Info reducida
        info_label = ttk.Label(
            self.frame,
            text=self.tr.get("focus_info", "Si está desactivado, funciona globalmente"),
            font=("-size", 8),
            bootstyle="secondary"
        )
        info_label.pack(pady=(6, 0))
    
    def _create_app_selector(self):
        """Crea el selector de aplicación"""
        app_select_container = ttk.Frame(self.frame)
        app_select_container.pack(fill="x")
        
        ttk.Label(
            app_select_container,
            text=self.tr.get("program_label", "Programa:"),
            font=("-size", 9, "-weight", "bold")
        ).grid(row=0, column=0, sticky="w", pady=4)
        
        self.app_combo = ttk.Combobox(
            app_select_container,
            state="readonly",
            width=40
        )
        self.app_combo.grid(row=0, column=1, padx=(8, 4), pady=4, sticky="ew")
        self.app_combo.bind("<<ComboboxSelected>>", lambda e: self.on_selected())
        
        self.btn_refresh = ttk.Button(
            app_select_container,
            text="🔄",
            command=self.on_refresh,
            bootstyle="info-outline",
            width=4
        )
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



class ControlButtonsComponent:
    """Componente de botones de control principal"""
    
    def __init__(self, parent, tr, on_toggle_callback, on_save_callback, 
                 on_minimize_callback, on_exit_callback):
        self.tr = tr
        self.on_toggle = on_toggle_callback
        
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", padx=20, pady=(0, 10))
        
        # Botón principal de activar/desactivar
        self.toggle_btn = ttk.Button(
            self.frame,
            text=self.tr.get("activate_script_btn", "Activar Script"),
            command=on_toggle_callback,
            bootstyle="success"
        )
        self.toggle_btn.pack(fill="x", pady=(0, 8), ipady=8)
        
        # Botones secundarios
        secondary_btns = ttk.Frame(self.frame)
        secondary_btns.pack(fill="x")
        
        self.btn_save = ttk.Button(
            secondary_btns,
            text=self.tr.get("save_btn", "Guardar Config"),
            command=on_save_callback,
            bootstyle="info"
        )
        self.btn_save.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        self.btn_minimize = ttk.Button(
            secondary_btns,
            text=self.tr.get("minimize_btn", "Minimizar"),
            command=on_minimize_callback,
            bootstyle="secondary"
        )
        self.btn_minimize.pack(side="left", fill="x", expand=True, padx=(4, 4))
        
        self.btn_exit = ttk.Button(
            secondary_btns,
            text=self.tr.get("exit_btn", "Salir"),
            command=on_exit_callback,
            bootstyle="danger-outline"
        )
        self.btn_exit.pack(side="left", fill="x", expand=True, padx=(4, 0))
    
    def set_toggle_state(self, is_active):
        """Actualiza el estado del botón de activación"""
        if is_active:
            self.toggle_btn.config(
                text=self.tr.get("stop_script_btn", "Detener Script"),
                bootstyle="warning"
            )
        else:
            self.toggle_btn.config(
                text=self.tr.get("activate_script_btn", "Activar Script"),
                bootstyle="success"
            )


class CommonKeysWindow:
    """Ventana que muestra las teclas comunes"""
    
    def __init__(self, parent, tr):
        self.tr = tr
        
        self.window = ttk.Toplevel(parent)
        self.window.title(self.tr.get("common_keys_title", "Teclas Comunes"))
        self.window.geometry("520x450")
        self.window.resizable(False, False)
        self.window.attributes('-topmost', True)
        self.window.transient(parent)
        self.window.grab_set()
        
        self._create_content()
    
    def _create_content(self):
        """Crea el contenido de la ventana"""
        main_container = ttk.Frame(self.window, padding=15)
        main_container.pack(fill="both", expand=True)
        
        # Título
        title = ttk.Label(
            main_container,
            text=self.tr.get("common_keys_desc", "Teclas más comunes para configurar:"),
            font=("-size", 13, "-weight", "bold")
        )
        title.pack(pady=(0, 15))
        
        # Texto scrollable
        text_frame = ttk.Frame(main_container)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        text_widget = ttk.Text(
            text_frame,
            yscrollcommand=scrollbar.set,
            wrap="word",
            font=("-family", "Consolas", "-size", 9)
        )
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Contenido de teclas
        common_keys = self._get_common_keys_text()
        text_widget.insert("1.0", common_keys.strip())
        text_widget.config(state="disabled")
        
        # Botón cerrar
        btn_close = ttk.Button(
            main_container,
            text=self.tr.get("close_btn", "Cerrar"),
            command=self.window.destroy,
            bootstyle="secondary"
        )
        btn_close.pack(pady=(10, 0), fill="x")
    
    def _get_common_keys_text(self):
        """Retorna el texto con las teclas comunes"""
        return f"""{self.tr.get("keys_letters", "Letras")}: a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z

{self.tr.get("keys_numbers", "Números")}: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9

{self.tr.get("keys_function", "Funciones")}: f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12

{self.tr.get("keys_modifiers", "Modificadores")}: shift, ctrl, alt, caps lock, tab, esc

{self.tr.get("keys_navigation", "Navegación")}: up, down, left, right, home, end, page up, page down

{self.tr.get("keys_special", "Especiales")}: space, enter, backspace, delete, insert

{self.tr.get("keys_numpad", "Teclado Numérico")}: num 0, num 1, num 2, num 3, num 4, num 5, num 6, num 7, num 8, num 9
   num lock, num +, num *, num -, num /, num enter, num .

{self.tr.get("keys_punctuation", "Puntuación")}: . (period), , (comma), ; (semicolon), ' (apostrophe)
   [ (left bracket), ] (right bracket), \\ (backslash)
   - (minus), = (equal), ` (grave)

{self.tr.get("keys_note", "Nota")}: {self.tr.get("keys_note_text", "Escribe el nombre de la tecla exactamente como aparece aquí.")}
"""
