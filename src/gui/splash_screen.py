"""
src/gui/splash_screen.py
Splash Screen Dinámico para KeyForge
Se adapta automáticamente a temas claros y oscuros y soporta traducción.
"""
import ttkbootstrap as ttk
from tkinter import Canvas

class SplashScreen:
    """
    Splash screen minimalista que respeta el tema de la aplicación.
    """
    
    def __init__(self, parent_root, tr_dict=None, title="KeyForge", version="1.0"):
        self.root = parent_root
        self.tr = tr_dict if tr_dict else {}
        self.title_text = title
        self.version_text = f"v{version}"
        
        # 1. Obtener el estilo y colores del tema actual
        self.style = ttk.Style()
        self.colors = self.style.colors
        
        self.window = None
        self.canvas = None
        self.progress_value = 0
        
        self._show()

    def _is_light_theme(self):
        """Detecta si el tema actual es claro (Light)"""
        return self.style.theme.type == 'light'

    def _show(self):
        """Inicializa y muestra la ventana"""
        self.window = ttk.Toplevel(self.root)
        self.window.overrideredirect(True) # Sin bordes
        self.window.attributes('-topmost', True)
        
        # Dimensiones compactas
        width = 360
        height = 160
        
        # Centrar en pantalla
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 2. Usar el color de fondo del tema (bg) en lugar de negro fijo
        bg_color = self.colors.bg 
        self.window.configure(bg=bg_color)
        
        # Canvas también usa el fondo del tema
        self.canvas = Canvas(
            self.window,
            width=width,
            height=height,
            bg=bg_color,
            highlightthickness=0
        )
        self.canvas.pack(fill='both', expand=True)
        
        self._draw_ui(width, height)
        self.window.update()

    def _draw_ui(self, w, h):
        """Dibuja los elementos usando colores dinámicos"""
        
        # Colores extraídos del tema
        fg_color = self.colors.fg            
        secondary_color = self.colors.secondary  
        border_color = self.colors.border    
        accent_color = self.colors.success   
        
        # Fondo de la barra de progreso
        if self._is_light_theme():
            bar_bg_color = "#e0e0e0" 
        else:
            bar_bg_color = "#111111" 

        # --- BORDES ---
        self.canvas.create_rectangle(
            0, 0, w-1, h-1,
            outline=border_color,
            width=1
        )
        
        # --- TÍTULO (Color adaptativo) ---
        self.canvas.create_text(
            w//2, 50,
            text=f"🔧 {self.title_text}",
            font=("Segoe UI", 18, "bold"),
            fill=fg_color,
            anchor="center"
        )
        
        # --- VERSIÓN ---
        self.canvas.create_text(
            w//2, 90,
            text=self.version_text,
            font=("Segoe UI", 8),
            fill=secondary_color,
            anchor="center"
        )
        
        # --- BARRA DE PROGRESO ---
        bar_y = 105
        bar_height = 6
        
        # Fondo de la barra
        self.progress_bg = self.canvas.create_rectangle(
            50, bar_y, w-50, bar_y + bar_height,
            fill=bar_bg_color,
            outline=border_color,
            width=1
        )
        
        # Relleno de la barra (Color de énfasis/Success)
        self.progress_bar = self.canvas.create_rectangle(
            50, bar_y, 50, bar_y + bar_height, 
            fill=accent_color,
            outline="",
            tags="progress"
        )
        
        # --- INFORMACIÓN DE ESTADO ---
        initial_text = self.tr.get("splash_init", "Initializing...")
        self.status_text_id = self.canvas.create_text(
            50, bar_y + 20,
            text=initial_text,
            font=("Segoe UI", 8),
            fill=secondary_color,
            anchor="w"
        )
        
        # Derecha: Porcentaje
        self.percent_text = self.canvas.create_text(
            w-50, bar_y + 20,
            text="0%",
            font=("Segoe UI", 8, "bold"),
            fill=accent_color,
            anchor="e"
        )

    def update_step(self, value, text):
        """Actualiza la visualización"""
        if not self.canvas: return
        
        self.progress_value = max(0, min(100, value))
        
        # Cálculo de geometría
        w = 360
        margin = 50
        max_bar_width = w - (margin * 2)
        current_width = max_bar_width * (self.progress_value / 100)
        
        bar_y = 105
        bar_height = 6
        
        self.canvas.coords(
            self.progress_bar, 
            margin, bar_y, 
            margin + current_width, bar_y + bar_height
        )
        
        # Usamos el color success del tema para consistencia
        fill_color = self.colors.success
            
        self.canvas.itemconfig(self.progress_bar, fill=fill_color)
        
        # Textos
        self.canvas.itemconfig(self.percent_text, text=f"{int(self.progress_value)}%")
        self.canvas.itemconfig(self.status_text_id, text=text)
        
        self.window.update_idletasks()

    def close(self):
        """Cierra el splash"""
        if self.window:
            self.window.destroy()
            self.window = None