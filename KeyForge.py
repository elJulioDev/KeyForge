import keyboard, threading, json
import ttkbootstrap as ttk
from tkinter import StringVar, BooleanVar, messagebox
import pygetwindow as gw
from pathlib import Path

# --- Configuración de Rutas ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"

# Crear carpeta data si no existe
DATA_DIR.mkdir(exist_ok=True)

# --- Configuración por Defecto ---
DEFAULT_CONFIG = {
    "mode": "mantener",
    "key_to_replace": "alt",
    "replacement_key": "shift",
    "enforce_app_focus": True,
    "target_app_name": ""
}

# --- Variables Globales ---
key_hook = None
toggle_state_active = False
target_app_is_active = False
current_mode = "mantener"
key_to_replace = "alt"
replacement_key = "shift"
is_listening = False
target_app_name = ""
enforce_app_focus = True
minimized_window = None
is_minimized = False
is_dragging = False
drag_start_x = 0
drag_start_y = 0

# --- Funciones de Configuración ---

def load_config():
    """
    Carga la configuración desde el archivo JSON.
    Si no existe, retorna la configuración por defecto.
    """
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"✅ Configuración cargada desde: {CONFIG_FILE}")
                return config
        else:
            print("📁 No se encontró archivo de configuración, usando valores por defecto")
            return DEFAULT_CONFIG.copy()
    except Exception as e:
        print(f"❌ Error al cargar configuración: {e}")
        return DEFAULT_CONFIG.copy()



def save_config():
    """
    Guarda la configuración actual en el archivo JSON.
    """
    try:
        config = {
            "mode": mode_var.get(),
            "key_to_replace": replace_key_var.get(),
            "replacement_key": replacement_key_var.get(),
            "enforce_app_focus": app_focus_var.get(),
            "target_app_name": app_combo.get() if app_focus_var.get() else ""
        }
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        messagebox.showinfo(
            "Configuración Guardada",
            f"✅ Configuración guardada exitosamente en:\n{CONFIG_FILE}"
        )
        print(f"💾 Configuración guardada: {config}")
        
    except Exception as e:
        messagebox.showerror(
            "Error",
            f"❌ No se pudo guardar la configuración:\n{str(e)}"
        )
        print(f"❌ Error al guardar configuración: {e}")



def apply_config(config):
    """
    Aplica la configuración cargada a la interfaz.
    """
    mode_var.set(config.get("mode", "mantener"))
    replace_key_var.set(config.get("key_to_replace", "alt"))
    replacement_key_var.set(config.get("replacement_key", "shift"))
    app_focus_var.set(config.get("enforce_app_focus", True))
    
    # Si hay un nombre de app guardado, intentar seleccionarlo
    saved_app = config.get("target_app_name", "")
    if saved_app and app_focus_var.get():
        try:
            app_combo.set(saved_app)
        except:
            pass



# --- Lógica de Verificación ---



def is_target_app_active():
    """
    Verifica si la ventana activa coincide con la aplicación objetivo.
    Si enforce_app_focus es False, siempre retorna True (funciona globalmente).
    """
    if not enforce_app_focus:
        return True
    
    try:
        active_window = gw.getActiveWindow()
        if active_window and target_app_name.lower() in active_window.title.lower():
            return True
    except Exception as e:
        pass
    return False



def update_app_status():
    """
    Actualiza la etiqueta de estado y la variable de caché.
    Se llama a sí misma cada 500ms.
    """
    global target_app_is_active
    
    if not enforce_app_focus:
        app_status_label.config(text="🌐 Modo Global (Todos los programas)", bootstyle="info")
        target_app_is_active = True
    else:
        if is_target_app_active():
            app_status_label.config(
                text=f"✅ {target_app_name} Detectado", 
                bootstyle="success"
            )
            target_app_is_active = True
        else:
            app_status_label.config(
                text=f"❌ Esperando {target_app_name}...", 
                bootstyle="info"
            )
            target_app_is_active = False
    
    root.after(500, update_app_status)



def refresh_windows_list():
    """
    Actualiza la lista de ventanas abiertas en el combobox.
    """
    try:
        all_windows = gw.getAllTitles()
        # Filtrar ventanas vacías y duplicados
        unique_windows = []
        seen = set()
        for window in all_windows:
            if window.strip() and window not in seen:
                unique_windows.append(window)
                seen.add(window)
        
        app_combo['values'] = unique_windows
        if unique_windows and not app_combo.get():
            app_combo.set(unique_windows[0])
    except Exception as e:
        app_combo['values'] = ["Error al obtener ventanas"]



def toggle_app_focus():
    """
    Alterna entre modo enfocado en una app específica o modo global.
    """
    global enforce_app_focus, target_app_name
    
    enforce_app_focus = app_focus_var.get()
    
    if enforce_app_focus:
        target_app_name = app_combo.get()
        app_combo.config(state="readonly")
        btn_refresh.config(state="normal")
    else:
        app_combo.config(state="disabled")
        btn_refresh.config(state="disabled")
    
    update_app_status()


def on_app_selected(event):
    """
    Actualiza target_app_name cuando se selecciona una nueva ventana del combobox.
    """
    global target_app_name
    if enforce_app_focus:
        target_app_name = app_combo.get()
        update_app_status()

# --- Lógica del Script ---

def handle_key_event(e):
    """
    Maneja todos los eventos de teclado capturados por el hook.
    """
    global toggle_state_active, current_mode, key_to_replace, replacement_key
    
    # Ignorar si no es la tecla configurada o si la app objetivo no está activa
    if e.name != key_to_replace or not target_app_is_active:
        return True  # Permitir que otras teclas funcionen normalmente


    # Lógica según el modo
    if current_mode == 'mantener':
        if e.event_type == keyboard.KEY_DOWN:
            keyboard.press(replacement_key)
        elif e.event_type == keyboard.KEY_UP:
            keyboard.release(replacement_key)
        
    elif current_mode == 'intercalar':
        if e.event_type == keyboard.KEY_DOWN:
            if toggle_state_active:
                keyboard.release(replacement_key)
                toggle_state_active = False
            else:
                keyboard.press(replacement_key)
                toggle_state_active = True


    # IMPORTANTE: Retornar False bloquea la tecla original
    return False

def toggle_script():
    global key_hook, toggle_state_active, current_mode, key_to_replace, replacement_key, target_app_name


    if key_hook:
        # --- DETENER EL SCRIPT ---
        keyboard.unhook(key_hook)
        key_hook = None
        
        if toggle_state_active:
            keyboard.release(replacement_key)
            toggle_state_active = False
            
        status_label.config(text="🔴 Script detenido", bootstyle="danger") 
        toggle_btn.config(text="▶ Activar Script", bootstyle="success")
        
        # Reactivar los controles
        radio_mantener.config(state="normal")
        radio_intercalar.config(state="normal")
        btn_detect_replace.config(state="normal")
        btn_detect_replacement.config(state="normal")
        btn_show_keys.config(state="normal")
        btn_save_config.config(state="normal")
        check_app_focus.config(state="normal")
        if enforce_app_focus:
            app_combo.config(state="readonly")
            btn_refresh.config(state="normal")
    
    else:
        # --- INICIAR EL SCRIPT ---
        current_mode = mode_var.get()
        key_to_replace = replace_key_var.get()
        replacement_key = replacement_key_var.get()
        
        if enforce_app_focus:
            target_app_name = app_combo.get()
        
        key_hook = keyboard.hook(handle_key_event, suppress=True)
        
        mode_text = "Mantener" if current_mode == "mantener" else "Intercalar"
        status_label.config(
            text=f"🟢 Activo: {key_to_replace} → {replacement_key} ({mode_text})", 
            bootstyle="success"
        )
        
        toggle_btn.config(text="⏸ Detener Script", bootstyle="warning")
        
        # Desactivar controles mientras está activo
        radio_mantener.config(state="disabled")
        radio_intercalar.config(state="disabled")
        btn_detect_replace.config(state="disabled")
        btn_detect_replacement.config(state="disabled")
        btn_show_keys.config(state="disabled")
        btn_save_config.config(state="disabled")
        check_app_focus.config(state="disabled")
        app_combo.config(state="disabled")
        btn_refresh.config(state="disabled")

# --- Funciones de Detección de Teclas ---

def listen_for_key(target_var, target_label):
    """
    Escucha y captura la siguiente tecla presionada.
    """
    global is_listening
    
    if is_listening:
        return
    
    is_listening = True
    original_text = target_label.cget("text")
    target_label.config(text="⌨️ Presiona una tecla...")
    
    def capture():
        global is_listening
        try:
            key = keyboard.read_event(suppress=False)
            while key.event_type != 'down':
                key = keyboard.read_event(suppress=False)
            
            captured_key = key.name
            target_var.set(captured_key)
            target_label.config(text=f"✅ {captured_key}")
            
        except Exception as e:
            target_label.config(text=f"❌ Error: {str(e)}")
        finally:
            is_listening = False
            root.after(2000, lambda: target_label.config(text=original_text))
    
    thread = threading.Thread(target=capture, daemon=True)
    thread.start()



def show_common_keys():
    """
    Muestra una ventana con las teclas más comunes.
    """
    keys_window = ttk.Toplevel(root)
    keys_window.title("Teclas Disponibles")
    keys_window.geometry("520x450")
    keys_window.resizable(False, False)
    
    # Frame principal con padding
    main_container = ttk.Frame(keys_window, padding=15)
    main_container.pack(fill="both", expand=True)
    
    # Título
    title = ttk.Label(
        main_container, 
        text="📋 Teclas Comunes del Teclado", 
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
    
    # Lista de teclas comunes
    common_keys = """
LETRAS:
a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z

NÚMEROS:
0, 1, 2, 3, 4, 5, 6, 7, 8, 9

TECLAS DE FUNCIÓN:
f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12

MODIFICADORES:
shift, ctrl, alt, caps lock, tab, esc

NAVEGACIÓN:
up, down, left, right, home, end, page up, page down

ESPECIALES:
space, enter, backspace, delete, insert

TECLADO NUMÉRICO:
num 0, num 1, num 2, num 3, num 4, num 5, num 6, num 7, num 8, num 9
num lock, num /, num *, num -, num +, num enter, num .

PUNTUACIÓN:
. (period), , (comma), ; (semicolon), ' (apostrophe)
[ (left bracket), ] (right bracket), \\ (backslash)
- (minus), = (equal), ` (grave)

NOTA: Para detectar una tecla, usa el botón "Detectar" 
y presiona la tecla deseada en tu teclado.
    """
    
    text_widget.insert("1.0", common_keys.strip())
    text_widget.config(state="disabled")
    
    # Botón de cerrar
    btn_close = ttk.Button(
        main_container,
        text="Cerrar",
        command=keys_window.destroy,
        bootstyle="secondary"
    )
    btn_close.pack(pady=(10, 0), fill="x")

def on_close():
    global key_hook
    if key_hook:
        keyboard.unhook(key_hook)
    if toggle_state_active:
        keyboard.release(replacement_key)
    root.destroy()

# --- Funciones de Minimización Personalizada ---

def start_move(event):
    """
    Guarda la posición inicial del mouse cuando empieza el arrastre.
    """
    global is_dragging, drag_start_x, drag_start_y
    
    # Guardar posición inicial del mouse
    minimized_window.x = event.x_root - minimized_window.winfo_x()
    minimized_window.y = event.y_root - minimized_window.winfo_y()
    
    # Guardar coordenadas para detectar si hubo movimiento
    drag_start_x = event.x_root
    drag_start_y = event.y_root
    is_dragging = False

def on_move(event):
    """
    Mueve la ventana flotante siguiendo el movimiento del mouse.
    """
    global is_dragging
    
    # Calcular nueva posición basada en la posición del mouse
    x = event.x_root - minimized_window.x
    y = event.y_root - minimized_window.y
    minimized_window.geometry(f"+{x}+{y}")
    
    # Marcar que hubo movimiento (arrastre)
    is_dragging = True

def on_release(event):
    """
    Detecta si fue un clic simple o un arrastre al soltar el botón.
    """
    global is_dragging, drag_start_x, drag_start_y
    
    # Calcular distancia movida
    distance = abs(event.x_root - drag_start_x) + abs(event.y_root - drag_start_y)
    
    # Si la distancia es menor a 5 píxeles, considerarlo un clic
    # Si es mayor, fue un arrastre y no hacer nada
    if distance < 5 and not is_dragging:
        restore_window()
    
    # Resetear flag de arrastre
    is_dragging = False

def restore_window():
    """
    Restaura la ventana principal desde el estado minimizado.
    """
    global is_minimized, minimized_window
    
    if minimized_window:
        minimized_window.destroy()
        minimized_window = None
    
    root.deiconify()
    root.attributes('-topmost', True)
    is_minimized = False


def minimize_custom():
    """
    Minimiza la ventana a un icono flotante personalizado.
    """
    global is_minimized, minimized_window
    
    if is_minimized:
        return
    
    # Ocultar ventana principal
    root.withdraw()
    
    # Crear ventana flotante pequeña
    minimized_window = ttk.Toplevel(root)
    minimized_window.overrideredirect(True)  # Sin bordes de ventana
    minimized_window.attributes('-topmost', True)
    
    # Tamaño y posición del icono flotante
    icon_size = 80
    x_pos = root.winfo_screenwidth() - icon_size - 20
    y_pos = 20
    
    minimized_window.geometry(f"{icon_size}x{icon_size}+{x_pos}+{y_pos}")
    
    # Frame contenedor con estilo
    container = ttk.Frame(minimized_window, bootstyle="dark")
    container.pack(fill="both", expand=True)
    
    # Botón con icono para restaurar
    restore_btn = ttk.Button(
        container,
        text="🔧\nKeyForge",
        bootstyle="info",
        cursor="hand2"
    )
    restore_btn.pack(fill="both", expand=True, padx=2, pady=2)
    
    # SOLUCIÓN MEJORADA: Vincular eventos de arrastre con detección
    # Eventos en la ventana principal
    minimized_window.bind("<Button-1>", start_move)
    minimized_window.bind("<B1-Motion>", on_move)
    minimized_window.bind("<ButtonRelease-1>", on_release)
    
    # Eventos en el contenedor
    container.bind("<Button-1>", start_move)
    container.bind("<B1-Motion>", on_move)
    container.bind("<ButtonRelease-1>", on_release)
    
    # Eventos en el botón
    restore_btn.bind("<Button-1>", start_move)
    restore_btn.bind("<B1-Motion>", on_move)
    restore_btn.bind("<ButtonRelease-1>", on_release)
    
    is_minimized = True

# ---- INTERFAZ GRÁFICA MEJORADA -------

root = ttk.Window(themename="darkly") 
root.title("KeyForge 🔧")
root.resizable(False, False)

window_width = 780
window_height = 900

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

pos_x = int((screen_width / 2) - (window_width / 2))
pos_y = int((screen_height / 2) - (window_height / 2))

root.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
root.attributes('-topmost', True)
root.protocol("WM_DELETE_WINDOW", on_close)

# Variables
mode_var = StringVar(value="mantener")
replace_key_var = StringVar(value="alt")
replacement_key_var = StringVar(value="shift")
app_focus_var = BooleanVar(value=True)

# Cargar configuración guardada
saved_config = load_config()
apply_config(saved_config)

# ------- SECCIÓN: ENCABEZADO --------

header_frame = ttk.Frame(root)
header_frame.pack(fill="x", padx=20, pady=(15, 10))

title_label = ttk.Label(
    header_frame,
    text="KeyForge",
    font=("-size", 18, "-weight", "bold")
)
title_label.pack()

subtitle_label = ttk.Label(
    header_frame,
    text="Remapeo Avanzado de Teclas",
    font=("-size", 9),
    bootstyle="secondary"
)
subtitle_label.pack()

# Separador
ttk.Separator(root, orient="horizontal").pack(fill="x", padx=20, pady=10)


# ---------- SECCIÓN: ESTADO -----------

status_frame = ttk.Frame(root)
status_frame.pack(fill="x", padx=20, pady=(0, 15))

status_label = ttk.Label(
    status_frame, 
    text="🔴 Script detenido", 
    bootstyle="danger", 
    font=("-size", 12, "-weight", "bold")
) 
status_label.pack()

app_status_label = ttk.Label(
    status_frame, 
    text="❌ Esperando configuración...", 
    bootstyle="info",
    font=("-size", 9)
)
app_status_label.pack(pady=(5, 0))

# -------------- SECCIÓN: APLICACIÓN OBJETIVO -------------

app_frame = ttk.LabelFrame(root, text="  🎯 Aplicación Objetivo  ", padding=15)
app_frame.pack(padx=20, pady=(0, 15), fill="x")

# Checkbox toggle
check_app_focus = ttk.Checkbutton(
    app_frame,
    text="Mantener enfoque en programa específico",
    variable=app_focus_var,
    command=toggle_app_focus,
    bootstyle="round-toggle"
)
check_app_focus.pack(anchor="w", pady=(0, 10))

# Selector de aplicación
app_select_container = ttk.Frame(app_frame)
app_select_container.pack(fill="x")

ttk.Label(
    app_select_container, 
    text="Programa:", 
    font=("-size", 9, "-weight", "bold")
).grid(row=0, column=0, sticky="w", pady=5)

app_combo = ttk.Combobox(
    app_select_container, 
    state="readonly", 
    width=42
)
app_combo.grid(row=0, column=1, padx=(10, 5), pady=5, sticky="ew")
app_combo.bind("<<ComboboxSelected>>", on_app_selected)

btn_refresh = ttk.Button(
    app_select_container,
    text="🔄",
    command=refresh_windows_list,
    bootstyle="info-outline",
    width=4
)
btn_refresh.grid(row=0, column=2, pady=5)

app_select_container.columnconfigure(1, weight=1)

# Info
info_label = ttk.Label(
    app_frame,
    text="💡 Desactiva el checkbox para funcionar en todos los programas",
    font=("-size", 8),
    bootstyle="secondary"
)
info_label.pack(pady=(10, 0))

# ---------- SECCIÓN: CONFIGURACIÓN DE TECLAS --------------

config_frame = ttk.LabelFrame(root, text="  ⚙️ Configuración de Teclas  ", padding=15)
config_frame.pack(padx=20, pady=(0, 15), fill="x")

# Grid para teclas
keys_grid = ttk.Frame(config_frame)
keys_grid.pack(fill="x")

# Tecla a Reemplazar
ttk.Label(
    keys_grid, 
    text="Tecla a Remplazar:", 
    font=("-size", 9, "-weight", "bold")
).grid(row=0, column=0, sticky="w", pady=8)

replace_entry = ttk.Entry(
    keys_grid, 
    textvariable=replace_key_var, 
    width=18,
    font=("-size", 10)
)
replace_entry.grid(row=0, column=1, padx=10, pady=8)

replace_status = ttk.Label(keys_grid, text="", width=12)
replace_status.grid(row=0, column=2, padx=5, pady=8)

btn_detect_replace = ttk.Button(
    keys_grid, 
    text="Detectar",
    command=lambda: listen_for_key(replace_key_var, replace_status),
    bootstyle="info-outline",
    width=12
)
btn_detect_replace.grid(row=0, column=3, pady=8)

# Tecla de Reemplazo
ttk.Label(
    keys_grid, 
    text="Remplazar con:", 
    font=("-size", 9, "-weight", "bold")
).grid(row=1, column=0, sticky="w", pady=8)

replacement_entry = ttk.Entry(
    keys_grid, 
    textvariable=replacement_key_var, 
    width=18,
    font=("-size", 10)
)
replacement_entry.grid(row=1, column=1, padx=10, pady=8)

replacement_status = ttk.Label(keys_grid, text="", width=12)
replacement_status.grid(row=1, column=2, padx=5, pady=8)

btn_detect_replacement = ttk.Button(
    keys_grid, 
    text="Detectar",
    command=lambda: listen_for_key(replacement_key_var, replacement_status),
    bootstyle="info-outline",
    width=12
)
btn_detect_replacement.grid(row=1, column=3, pady=8)

# Botón de ayuda
btn_show_keys = ttk.Button(
    config_frame,
    text="📋 Ver Lista de Teclas Comunes",
    command=show_common_keys,
    bootstyle="secondary-outline"
)
btn_show_keys.pack(fill="x", pady=(15, 0))

# ------------ SECCIÓN: MODO DE OPERACIÓN ---------------

mode_frame = ttk.LabelFrame(root, text="  🎮 Modo de Operación  ", padding=15)
mode_frame.pack(padx=20, pady=(0, 15), fill="x")

radio_mantener = ttk.Radiobutton(
    mode_frame, 
    text="⏺ Mantener (Hold) - Presiona mientras sostienes la tecla", 
    variable=mode_var, 
    value="mantener"
)
radio_mantener.pack(anchor="w", pady=5)

radio_intercalar = ttk.Radiobutton(
    mode_frame, 
    text="🔄 Intercalar (Toggle) - Alterna entre activado/desactivado", 
    variable=mode_var, 
    value="intercalar"
)
radio_intercalar.pack(anchor="w", pady=5)

# ----------- SECCIÓN: CONTROLES PRINCIPALES ------------

controls_frame = ttk.Frame(root)
controls_frame.pack(fill="x", padx=20, pady=(0, 15))

# Grid de botones principales
btn_grid = ttk.Frame(controls_frame)
btn_grid.pack(fill="x")

# Botón activar/detener (más grande)
toggle_btn = ttk.Button(
    btn_grid, 
    text="▶ Activar Script", 
    command=toggle_script, 
    bootstyle="success"
)
toggle_btn.pack(fill="x", pady=(0, 8), ipady=8)

# Grid para botones secundarios
secondary_btns = ttk.Frame(btn_grid)
secondary_btns.pack(fill="x")

btn_save_config = ttk.Button(
    secondary_btns,
    text="💾 Guardar",
    command=save_config,
    bootstyle="info"
)
btn_save_config.pack(side="left", fill="x", expand=True, padx=(0, 4))

btn_minimize_custom = ttk.Button(
    secondary_btns,
    text="➖ Minimizar",
    command=minimize_custom,
    bootstyle="secondary"
)
btn_minimize_custom.pack(side="left", fill="x", expand=True, padx=(4, 4))

exit_btn = ttk.Button(
    secondary_btns, 
    text="✕ Salir", 
    command=on_close, 
    bootstyle="danger-outline"
)
exit_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))

# ------- FOOTER -------------

ttk.Separator(root, orient="horizontal").pack(fill="x", padx=20, pady=(10, 10))

footer_frame = ttk.Frame(root)
footer_frame.pack(fill="x", padx=20, pady=(0, 15))

config_info = ttk.Label(
    footer_frame,
    text=f"📂 Configuración: {CONFIG_FILE.name}",
    font=("-size", 8),
    bootstyle="secondary"
)
config_info.pack()

version_label = ttk.Label(
    footer_frame,
    text="v1.1.0 • KeyForge",
    font=("-size", 7),
    bootstyle="secondary"
)
version_label.pack()

# Inicialización
refresh_windows_list()
toggle_app_focus()
update_app_status()

root.mainloop()
