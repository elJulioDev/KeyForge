"""
Ventana minimizada flotante
"""
import ttkbootstrap as ttk
from ..utils.window_manager import WindowManager


class MinimizedWindow:
    """Ventana flotante minimalista para estado minimizado"""
    
    def __init__(self, parent, on_restore_callback, on_toggle_callback):
        self.parent = parent
        self.on_restore = on_restore_callback
        self.on_toggle = on_toggle_callback  # Guardamos la función toggle
        self.window = None
        self.window_manager = WindowManager()
        self.canvas = None # Referencia al canvas para redibujar
        self.size = 90     # Tamaño guardado
    
    # 1. MODIFICAMOS show PARA ACEPTAR EL ESTADO
    def show(self, is_active=False):
        """Muestra la ventana minimizada con el estado visual correspondiente"""
        if self.window:
            return
        
        # Crear ventana flotante
        self.window = ttk.Toplevel(self.parent)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.0) # Inicia invisible para fade-in
        
        # Tamaño
        size = 90
        # Posición inicial (Centrado en pantalla)
        screen_w = self.parent.winfo_screenwidth()
        screen_h = self.parent.winfo_screenheight()
        
        # Fórmula: (AnchoPantalla / 2) - (AnchoVentana / 2)
        x_pos = int((screen_w / 2) - (size / 2))
        y_pos = int((screen_h / 2) - (size / 2))
        
        self.window.geometry(f"{size}x{size}+{x_pos}+{y_pos}")
        self.window.configure(background='#0f0f0f')
        
        # 2. Guardamos el canvas como self.canvas
        self.canvas = ttk.Canvas(
            self.window,
            width=self.size,
            height=self.size,
            highlightthickness=0,
            bg="#0f0f0f"
        )
        self.canvas.pack(fill="both", expand=True)
        
        # 2. PASAMOS EL ESTADO AL DIBUJADO
        self._draw_pro_icon(self.canvas, size, is_active)
        
        # Eventos
        self._bind_events(self.canvas)
        
        # Animación de entrada
        self._fade_in()
    
    def update_visuals(self, is_active):
        """Redibuja el icono según el nuevo estado (Activo/Inactivo)"""
        if self.canvas:
            self.canvas.delete("all") # Limpia el dibujo anterior
            self._draw_pro_icon(self.canvas, self.size, is_active)

    def _draw_pro_icon(self, canvas, s, is_active):
        """
        Dibuja un icono moderno. 
        Cambia de color según is_active.
        """
        pad = 5
        r = 16 
        
        bg_color = "#1a1a1a"
        
        # 3. LÓGICA DE COLORES DINÁMICOS
        if is_active:
            # ESTADO ACTIVO: Colores brillantes (Verde)
            accent_color = "#00bc8c"  # Borde verde neón
            icon_color = "#ffffff"    # Icono blanco brillante
            dot_color = "#00ff00"     # LED verde encendido
            key_fill = "#2b2b2b"      # Tecla normal
        else:
            # ESTADO INACTIVO: Colores apagados (Gris)
            accent_color = "#444444"  # Borde gris oscuro
            icon_color = "#777777"    # Icono grisáceo
            dot_color = "#222222"     # LED apagado (casi negro)
            key_fill = "#1f1f1f"      # Tecla más oscura
            
        # Borde exterior (Glow)
        self._round_rect(canvas, pad, pad, s-pad, s-pad, r, outline=accent_color, width=2, fill=bg_color)
        
        # Representación de una Tecla
        k_pad = 22
        # Sombra tecla
        self._round_rect(canvas, k_pad, k_pad-2, s-k_pad, s-k_pad-2, 8, fill="#0d0d0d", outline="") 
        # Cara tecla (Usa color dinámico)
        self._round_rect(canvas, k_pad, k_pad, s-k_pad, s-k_pad, 8, fill=key_fill, outline="#333333", width=1) 
        
        # Icono (Usa color dinámico)
        canvas.create_text(s/2, s/2, text="🔧", font=("Segoe UI Emoji", 28), fill=icon_color)
        
        # Indicador de estado (LED)
        ind_r = 3
        ind_x = s - 15
        ind_y = 15
        # El LED usa el color dinámico
        canvas.create_oval(ind_x-ind_r, ind_y-ind_r, ind_x+ind_r, ind_y+ind_r, fill=dot_color, outline="")

    def _round_rect(self, canvas, x1, y1, x2, y2, radius=25, **kwargs):
        """Función auxiliar para dibujar rectángulos redondeados"""
        points = [x1+radius, y1,
                  x1+radius, y1,
                  x2-radius, y1,
                  x2-radius, y1,
                  x2, y1,
                  x2, y1+radius,
                  x2, y1+radius,
                  x2, y2-radius,
                  x2, y2-radius,
                  x2, y2,
                  x2-radius, y2,
                  x2-radius, y2,
                  x1+radius, y2,
                  x1+radius, y2,
                  x1, y2,
                  x1, y2-radius,
                  x1, y2-radius,
                  x1, y1+radius,
                  x1, y1+radius,
                  x1, y1]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def _bind_events(self, widget):
        """Configura eventos de arrastre y click"""
        widget.bind("<Double-Button-1>", lambda e: self._restore())
        widget.bind("<ButtonPress-1>", lambda e: self.window_manager.start_drag(e, self.window))
        widget.bind("<B1-Motion>", lambda e: self.window_manager.drag(e, self.window))
        widget.bind("<ButtonRelease-1>", self._on_release)
        widget.bind("<Button-3>", lambda e: self.on_toggle())
        def on_enter(e):
            self.window.attributes('-alpha', 1.0)
            widget.config(cursor="hand2")
            
            
        def on_leave(e):
            self.window.attributes('-alpha', 0.9)
            widget.config(cursor="")

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _on_release(self, event):
        if self.window_manager.end_drag(event):
            self._restore()

    def _restore(self):
        self.hide()
        self.on_restore()

    def _fade_in(self, alpha=0.0):
        if self.window and alpha < 0.9:
            self.window.attributes('-alpha', alpha)
            self.parent.after(15, lambda: self._fade_in(alpha + 0.05))
    
    def hide(self):
        if self.window:
            self.window.destroy()
            self.window = None
            self.canvas = None
    
    def is_visible(self):
        return self.window is not None