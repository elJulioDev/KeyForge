import keyboard, threading, json
import ttkbootstrap as ttk
from tkinter import StringVar, BooleanVar, messagebox
import pygetwindow as gw
from pathlib import Path

# --- Configuración de Rutas ---
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LANG_FILE = DATA_DIR / "lang.json"
CONFIG_FILE = DATA_DIR / "config.json"

# Carga configuración
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = json.load(f)
# Carga idiomas
with open(LANG_FILE, 'r', encoding='utf-8') as f:
    translations = json.load(f)

# Lee el idioma elegido (ejemplo: 'es' o 'en')
lang = config.get("lang", "es")
# Selecciona las traducciones
tr = translations.get(lang, translations['es'])

# Crear carpeta data si no existe
DATA_DIR.mkdir(exist_ok=True)

# --- Configuración por Defecto ---
DEFAULT_CONFIG = {
    "mode": "mantener",
    "key_to_replace": "alt",
    "replacement_key": "shift",
    "enforce_app_focus": True,
    "target_app_name": "",
    "lang": "en"
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
    Guarda la configuración actual en el archivo JSON pero preservando otras claves (como 'lang').
    """
    try:
        # 1. Leer la config actual (o iniciar con DEFAULT)
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
        else:
            current_config = {}

        # 2. Actualizar/configurar solo los campos editables
        current_config.update({
            "mode": mode_var.get(),
            "key_to_replace": replace_key_var.get(),
            "replacement_key": replacement_key_var.get(),
            "enforce_app_focus": app_focus_var.get(),
            "target_app_name": app_combo.get() if app_focus_var.get() else ""
        })

        # 3. Guardar TODO el config (no sólo lo nuevo)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, indent=4, ensure_ascii=False)

        messagebox.showinfo(
            tr["saved_title"],
            tr["saved_msg"].format(config_file=CONFIG_FILE)
        )
        print(tr["saved_msg"].format(config_file=CONFIG_FILE))
    except Exception as e:
        messagebox.showerror(
            tr["error_title"],
            tr["error_msg"].format(err=str(e))
        )
        print(tr["error_msg"].format(err=e))


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
        app_status_label.config(
            text=tr["global_mode"],  # 🌐 Modo Global (Todos los programas)
            bootstyle="info"
        )
        target_app_is_active = True
    else:
        if is_target_app_active():
            app_status_label.config(
                text=tr["app_detected"].format(app=target_app_name),  # ✅ {app} Detectado
                bootstyle="success"
            )
            target_app_is_active = True
        else:
            app_status_label.config(
                text=tr["waiting_app"].format(app=target_app_name),   # ❌ Esperando {app}...
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
        app_combo['values'] = [tr["refresh_error"]]


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
            
        status_label.config(text=tr["status_stopped"], bootstyle="danger") 
        toggle_btn.config(text=tr["activate_script_btn"], bootstyle="success")
        
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
        
        mode_text = tr["hold"] if current_mode == "mantener" else tr["toggle"]
        status_label.config(
            text=tr["status_running"].format(
                src=key_to_replace,
                dst=replacement_key,
                mode=mode_text
            ), 
            bootstyle="success"
        )
        
        toggle_btn.config(text=tr["stop_script_btn"], bootstyle="warning")
        
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
    target_label.config(text=tr["press_key_label"])
    
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
    """Muestra una ventana con las teclas más comunes."""
    keys_window = ttk.Toplevel(root)
    keys_window.title(tr["common_keys_title"])
    keys_window.geometry("520x450")
    keys_window.resizable(False, False)
    
    # Asegurar que la ventana aparezca encima
    keys_window.attributes('-topmost', True)
    keys_window.transient(root)
    keys_window.grab_set()
    
    # Frame principal con padding
    main_container = ttk.Frame(keys_window, padding=15)
    main_container.pack(fill="both", expand=True)
    
    # Título
    title = ttk.Label(
        main_container,
        text=tr["common_keys_desc"],
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
    
    # Lista de teclas comunes con traducciones
    common_keys = f"""
{tr["keys_letters"]}
a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z


{tr["keys_numbers"]}
0, 1, 2, 3, 4, 5, 6, 7, 8, 9


{tr["keys_function"]}
f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, f12


{tr["keys_modifiers"]}
shift, ctrl, alt, caps lock, tab, esc


{tr["keys_navigation"]}
up, down, left, right, home, end, page up, page down


{tr["keys_special"]}
space, enter, backspace, delete, insert


{tr["keys_numpad"]}
num 0, num 1, num 2, num 3, num 4, num 5, num 6, num 7, num 8, num 9
num lock, num *, num +, num -, num /, num enter, num .


{tr["keys_punctuation"]}
. (period), , (comma), ; (semicolon), ' (apostrophe)
[ (left bracket), ] (right bracket), \\ (backslash)
- (minus), = (equal), ` (grave)


{tr["keys_note"]}
{tr["keys_note_text"]}
"""
    
    text_widget.insert("1.0", common_keys.strip())
    text_widget.config(state="disabled")
    
    # Botón de cerrar
    btn_close = ttk.Button(
        main_container,
        text=tr["close_btn"],
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
    Minimiza la ventana a un icono flotante ultra profesional con diseño moderno.
    """
    global is_minimized, minimized_window

    if is_minimized:
        return

    # Ocultar ventana principal
    root.withdraw()

    # Crear ventana flotante minimalista
    minimized_window = ttk.Toplevel(root)
    minimized_window.overrideredirect(True)
    minimized_window.attributes('-topmost', True)
    minimized_window.attributes('-alpha', 0.95)  # Ligera transparencia

    # Tamaño y posición optimizados
    icon_size = 100
    x_pos = root.winfo_screenwidth() - icon_size - 25
    y_pos = 25
    
    minimized_window.geometry(f"{icon_size}x{icon_size}+{x_pos}+{y_pos}")

    # Frame contenedor moderno
    container = ttk.Frame(minimized_window, bootstyle="dark")
    container.pack(fill="both", expand=True)

    # Canvas para diseño profesional con gradiente
    canvas = ttk.Canvas(
        container,
        width=icon_size,
        height=icon_size,
        highlightthickness=0,
        bg="#0d0d0d"
    )
    canvas.pack(fill="both", expand=True)

    # Sombra exterior sutil
    shadow_offset = 2
    canvas.create_oval(
        shadow_offset + 4, shadow_offset + 4,
        icon_size - 4, icon_size - 4,
        fill="#0a0a0a",
        outline=""
    )

    # Círculo base con gradiente simulado (capas concéntricas)
    margin = 6
    
    # Capa exterior - tono más oscuro
    canvas.create_oval(
        margin, margin,
        icon_size - margin, icon_size - margin,
        fill="#cc5500",
        outline="#ff6600",
        width=2
    )
    
    # Capa media - tono principal
    canvas.create_oval(
        margin + 6, margin + 6,
        icon_size - margin - 6, icon_size - margin - 6,
        fill="#ff7722",
        outline=""
    )
    
    # Capa superior - resaltado para efecto degradado
    canvas.create_oval(
        margin + 12, margin + 12,
        icon_size - margin - 12, icon_size - margin - 12,
        fill="#ff9944",
        outline=""
    )
    
    # Punto brillante (highlight) para efecto 3D
    canvas.create_oval(
        margin + 18, margin + 15,
        margin + 28, margin + 25,
        fill="#ffbb66",
        outline=""
    )

    # Icono principal - herramienta
    canvas.create_text(
        icon_size // 2,
        icon_size // 2 - 10,
        text="🔧",
        font=("-size", 26),
        fill="white"
    )
    
    # Texto identificador profesional
    canvas.create_text(
        icon_size // 2,
        icon_size // 2 + 20,
        text="KeyForge",
        font=("-family", "Segoe UI", "-size", 9, "-weight", "bold"),
        fill="white"
    )
    
    # Borde brillante final
    canvas.create_oval(
        margin - 1, margin - 1,
        icon_size - margin + 1, icon_size - margin + 1,
        outline="#ffaa44",
        width=1
    )

    # Eventos de interacción
    def on_enter(e):
        canvas.config(cursor="hand2")
        minimized_window.attributes('-alpha', 1.0)  # Opacidad total al hover
    
    def on_leave(e):
        canvas.config(cursor="")
        minimized_window.attributes('-alpha', 0.95)
    
    # Bind de eventos
    minimized_window.bind("<Button-1>", start_move)
    minimized_window.bind("<B1-Motion>", on_move)
    minimized_window.bind("<ButtonRelease-1>", on_release)
    minimized_window.bind("<Enter>", on_enter)
    minimized_window.bind("<Leave>", on_leave)
    
    canvas.bind("<Button-1>", start_move)
    canvas.bind("<B1-Motion>", on_move)
    canvas.bind("<ButtonRelease-1>", on_release)
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    
    container.bind("<Button-1>", start_move)
    container.bind("<B1-Motion>", on_move)
    container.bind("<ButtonRelease-1>", on_release)

    # Animación de entrada (opcional)
    def fade_in(alpha=0.0):
        if alpha < 0.95:
            minimized_window.attributes('-alpha', alpha)
            root.after(10, lambda: fade_in(alpha + 0.05))
    
    fade_in()

    is_minimized = True

# ---- INTERFAZ GRÁFICA OPTIMIZADA Y PROFESIONAL CON ARRASTRE -------

root = ttk.Window(themename="darkly") 
root.overrideredirect(True)
root.title("KeyForge 🔧")
root.resizable(False, False)

# Dimensiones optimizadas
window_width = 750
window_height = 850

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

pos_x = int((screen_width / 2) - (window_width / 2))
pos_y = int((screen_height / 2) - (window_height / 2))

root.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
root.attributes('-topmost', True)
root.protocol("WM_DELETE_WINDOW", on_close)

# Variables globales para arrastre de ventana principal
window_drag_x = 0
window_drag_y = 0

def start_window_drag(event):
    """Inicia el arrastre de la ventana principal."""
    global window_drag_x, window_drag_y
    window_drag_x = event.x
    window_drag_y = event.y

def drag_window(event):
    """Arrastra la ventana principal."""
    x = root.winfo_x() + event.x - window_drag_x
    y = root.winfo_y() + event.y - window_drag_y
    root.geometry(f"+{x}+{y}")

# Variables
mode_var = StringVar(value="mantener")
replace_key_var = StringVar(value="alt")
replacement_key_var = StringVar(value="shift")
app_focus_var = BooleanVar(value=True)

# Cargar configuración guardada
saved_config = load_config()
apply_config(saved_config)

# ------- SECCIÓN: ENCABEZADO COMPACTO (ÁREA DE ARRASTRE) --------

header_frame = ttk.Frame(root)
header_frame.pack(fill="x", padx=20, pady=(12, 8))

# Hacer el encabezado arrastrable
header_frame.bind("<Button-1>", start_window_drag)
header_frame.bind("<B1-Motion>", drag_window)

title_label = ttk.Label(
    header_frame,
    text="KeyForge",
    font=("-size", 16, "-weight", "bold")
)
title_label.pack()

# Hacer el título arrastrable también
title_label.bind("<Button-1>", start_window_drag)
title_label.bind("<B1-Motion>", drag_window)

# Separador delgado
ttk.Separator(root, orient="horizontal").pack(fill="x", padx=20, pady=8)

# ---------- SECCIÓN: ESTADO COMPACTO -----------

status_frame = ttk.Frame(root)
status_frame.pack(fill="x", padx=20, pady=(0, 10))

status_label = ttk.Label(
    status_frame, 
    text=tr["status_stopped"],
    bootstyle="danger", 
    font=("-size", 11, "-weight", "bold")
) 
status_label.pack()

app_status_label = ttk.Label(
    status_frame, 
    text=tr["waiting_config"], 
    bootstyle="info",
    font=("-size", 8)
)
app_status_label.pack(pady=(3, 0))

# -------------- SECCIÓN: APLICACIÓN OBJETIVO -------------

app_frame = ttk.LabelFrame(root, text=tr["target_app_title"], padding=12)
app_frame.pack(padx=20, pady=(0, 10), fill="x")

# Checkbox toggle compacto
check_app_focus = ttk.Checkbutton(
    app_frame,
    text=tr["focus_checkbox"], 
    variable=app_focus_var,
    command=toggle_app_focus,
    bootstyle="round-toggle"
)
check_app_focus.pack(anchor="w", pady=(0, 8))

# Selector de aplicación
app_select_container = ttk.Frame(app_frame)
app_select_container.pack(fill="x")

ttk.Label(
    app_select_container, 
    text=tr["program_label"],  
    font=("-size", 9, "-weight", "bold")
).grid(row=0, column=0, sticky="w", pady=4)

app_combo = ttk.Combobox(
    app_select_container, 
    state="readonly", 
    width=40
)
app_combo.grid(row=0, column=1, padx=(8, 4), pady=4, sticky="ew")
app_combo.bind("<<ComboboxSelected>>", on_app_selected)

btn_refresh = ttk.Button(
    app_select_container,
    text="🔄",
    command=refresh_windows_list,
    bootstyle="info-outline",
    width=4
)
btn_refresh.grid(row=0, column=2, pady=4)

app_select_container.columnconfigure(1, weight=1)

# Info reducida
info_label = ttk.Label(
    app_frame,
    text=tr["focus_info"],
    font=("-size", 8),
    bootstyle="secondary"
)
info_label.pack(pady=(6, 0))

# ---------- SECCIÓN: CONFIGURACIÓN DE TECLAS --------------

config_frame = ttk.LabelFrame(root, text=tr["key_config_title"], padding=12)
config_frame.pack(padx=20, pady=(0, 10), fill="x")

# Grid para teclas compacto
keys_grid = ttk.Frame(config_frame)
keys_grid.pack(fill="x")

# Tecla a Reemplazar
ttk.Label(
    keys_grid, 
    text=tr["replace_label"],
    font=("-size", 9, "-weight", "bold")
).grid(row=0, column=0, sticky="w", pady=6)

replace_entry = ttk.Entry(
    keys_grid, 
    textvariable=replace_key_var, 
    width=16,
    font=("-size", 9)
)
replace_entry.grid(row=0, column=1, padx=8, pady=6)

replace_status = ttk.Label(keys_grid, text="", width=10)
replace_status.grid(row=0, column=2, padx=4, pady=6)

btn_detect_replace = ttk.Button(
    keys_grid, 
    text=tr["detect_btn"],
    command=lambda: listen_for_key(replace_key_var, replace_status),
    bootstyle="info-outline",
    width=10
)
btn_detect_replace.grid(row=0, column=3, pady=6)

# Tecla de Reemplazo
ttk.Label(
    keys_grid, 
    text=tr["with_label"],
    font=("-size", 9, "-weight", "bold")
).grid(row=1, column=0, sticky="w", pady=6)

replacement_entry = ttk.Entry(
    keys_grid, 
    textvariable=replacement_key_var, 
    width=16,
    font=("-size", 9)
)
replacement_entry.grid(row=1, column=1, padx=8, pady=6)

replacement_status = ttk.Label(keys_grid, text="", width=10)
replacement_status.grid(row=1, column=2, padx=4, pady=6)

btn_detect_replacement = ttk.Button(
    keys_grid, 
    text=tr["detect_btn"],
    command=lambda: listen_for_key(replacement_key_var, replacement_status),
    bootstyle="info-outline",
    width=10
)
btn_detect_replacement.grid(row=1, column=3, pady=6)

# Botón de ayuda compacto
btn_show_keys = ttk.Button(
    config_frame,
    text=tr["show_keys_btn"],
    command=show_common_keys,
    bootstyle="secondary-outline"
)
btn_show_keys.pack(fill="x", pady=(10, 0))

# ------------ SECCIÓN: MODO DE OPERACIÓN ---------------

mode_frame = ttk.LabelFrame(root, text=tr["mode_title"], padding=12)
mode_frame.pack(padx=20, pady=(0, 10), fill="x")

radio_mantener = ttk.Radiobutton(
    mode_frame, 
    text=tr["hold_mode"],
    variable=mode_var, 
    value="mantener"
)
radio_mantener.pack(anchor="w", pady=4)

radio_intercalar = ttk.Radiobutton(
    mode_frame, 
    text=tr["toggle_mode"], 
    variable=mode_var, 
    value="intercalar"
)
radio_intercalar.pack(anchor="w", pady=4)

# ----------- SECCIÓN: CONTROLES PRINCIPALES ------------

controls_frame = ttk.Frame(root)
controls_frame.pack(fill="x", padx=20, pady=(0, 10))

# Botón activar/detener destacado
toggle_btn = ttk.Button(
    controls_frame, 
    text=tr["activate_script_btn"],
    command=toggle_script, 
    bootstyle="success"
)
toggle_btn.pack(fill="x", pady=(0, 8), ipady=8)

# Grid para botones secundarios
secondary_btns = ttk.Frame(controls_frame)
secondary_btns.pack(fill="x")

btn_save_config = ttk.Button(
    secondary_btns,
    text=tr["save_btn"],
    command=save_config,
    bootstyle="info"
)
btn_save_config.pack(side="left", fill="x", expand=True, padx=(0, 4))

btn_minimize_custom = ttk.Button(
    secondary_btns,
    text=tr["minimize_btn"],
    command=minimize_custom,
    bootstyle="secondary"
)
btn_minimize_custom.pack(side="left", fill="x", expand=True, padx=(4, 4))

exit_btn = ttk.Button(
    secondary_btns, 
    text=tr["exit_btn"],
    command=on_close, 
    bootstyle="danger-outline"
)
exit_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))

# ------- FOOTER VISIBLE -------------

ttk.Separator(root, orient="horizontal").pack(fill="x", padx=20, pady=8)

footer_frame = ttk.Frame(root)
footer_frame.pack(fill="x", padx=20, pady=(0, 12))

config_info = ttk.Label(
    footer_frame,
    text=f"📂 Config: {CONFIG_FILE.name}",
    font=("-size", 8),
    bootstyle="secondary"
)
config_info.pack()

version_label = ttk.Label(
    footer_frame,
    text="v1.1.1 • KeyForge",
    font=("-size", 8),
    bootstyle="secondary"
)
version_label.pack(pady=(2, 0))

# Inicialización
refresh_windows_list()
toggle_app_focus()
update_app_status()

root.mainloop()
