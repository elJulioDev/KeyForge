"""
Ventana minimizada flotante
"""
import ttkbootstrap as ttk
from ..utils.window_manager import WindowManager


class MinimizedWindow:
    """Ventana flotante minimalista para estado minimizado"""
    
    def __init__(self, parent, on_restore_callback):
        self.parent = parent
        self.on_restore = on_restore_callback
        self.window = None
        self.window_manager = WindowManager()
    
    def show(self):
        """Muestra la ventana minimizada"""
        if self.window:
            return
        
        # Crear ventana flotante
        self.window = ttk.Toplevel(self.parent)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.95)
        
        # Tamaño y posición
        icon_size = 100
        x_pos = self.parent.winfo_screenwidth() - icon_size - 25
        y_pos = 25
        self.window.geometry(f"{icon_size}x{icon_size}+{x_pos}+{y_pos}")
        
        # Contenedor
        container = ttk.Frame(self.window, bootstyle="dark")
        container.pack(fill="both", expand=True)
        
        # Canvas para el diseño
        canvas = ttk.Canvas(
            container,
            width=icon_size,
            height=icon_size,
            highlightthickness=0,
            bg="#0d0d0d"
        )
        canvas.pack(fill="both", expand=True)
        
        # Diseño del icono (gradiente simulado)
        self._draw_icon(canvas, icon_size)
        
        # Eventos de interacción
        self._bind_events(canvas, container)
        
        # Animación de entrada
        self._fade_in()
    
    def _draw_icon(self, canvas, size):
        """Dibuja el icono en el canvas"""
        margin = 6
        
        # Sombra
        canvas.create_oval(8, 8, size - 4, size - 4, fill="#0a0a0a", outline="")
        
        # Capas de gradiente
        canvas.create_oval(margin, margin, size - margin, size - margin,
                          fill="#cc5500", outline="#ff6600", width=2)
        canvas.create_oval(margin + 6, margin + 6, size - margin - 6, size - margin - 6,
                          fill="#ff7722", outline="")
        canvas.create_oval(margin + 12, margin + 12, size - margin - 12, size - margin - 12,
                          fill="#ff9944", outline="")
        
        # Highlight
        canvas.create_oval(margin + 18, margin + 15, margin + 28, margin + 25,
                          fill="#ffbb66", outline="")
        
        # Icono y texto
        canvas.create_text(size // 2, size // 2 - 10, text="🔧",
                          font=("-size", 26), fill="white")
        canvas.create_text(size // 2, size // 2 + 20, text="KeyForge",
                          font=("-family", "Segoe UI", "-size", 9, "-weight", "bold"),
                          fill="white")
        
        # Borde brillante
        canvas.create_oval(margin - 1, margin - 1, size - margin + 1, size - margin + 1,
                          outline="#ffaa44", width=1)
    
    def _bind_events(self, canvas, container):
        """Configura los eventos de mouse"""
        def on_press(e):
            self.window_manager.start_drag(e, self.window)
        
        def on_drag(e):
            self.window_manager.drag(e, self.window)
        
        def on_release(e):
            if self.window_manager.end_drag(e):
                self.hide()
                self.on_restore()
        
        def on_enter(e):
            canvas.config(cursor="hand2")
            self.window.attributes('-alpha', 1.0)
        
        def on_leave(e):
            canvas.config(cursor="")
            self.window.attributes('-alpha', 0.95)
        
        # Bind a todos los elementos
        for widget in [self.window, canvas, container]:
            widget.bind("<ButtonPress-1>", on_press)
            widget.bind("<B1-Motion>", on_drag)
            widget.bind("<ButtonRelease-1>", on_release)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
    
    def _fade_in(self, alpha=0.0):
        """Animación de aparición"""
        if self.window and alpha < 0.95:
            self.window.attributes('-alpha', alpha)
            self.parent.after(10, lambda: self._fade_in(alpha + 0.05))
    
    def hide(self):
        """Oculta y destruye la ventana minimizada"""
        if self.window:
            self.window.destroy()
            self.window = None
    
    def is_visible(self):
        """Verifica si la ventana está visible"""
        return self.window is not None
