"""
Utilidades para manejo de ventanas
"""
import sys


class WindowManager:
    """Gestiona operaciones de ventanas como arrastre y centrado dinámico"""
    
    def __init__(self):
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.offset_x = 0
        self.offset_y = 0
    
    def start_drag(self, event, window):
        """Inicia el arrastre de una ventana"""
        self.offset_x = event.x_root - window.winfo_x()
        self.offset_y = event.y_root - window.winfo_y()
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.is_dragging = False
    
    def drag(self, event, window):
        """Arrastra la ventana siguiendo el mouse"""
        x = event.x_root - self.offset_x
        y = event.y_root - self.offset_y
        window.geometry(f"+{x}+{y}")
        self.is_dragging = True
    
    def end_drag(self, event):
        """Finaliza el arrastre y detecta si fue un clic o arrastre"""
        distance = abs(event.x_root - self.drag_start_x) + abs(event.y_root - self.drag_start_y)
        was_click = distance < 5 and not self.is_dragging
        self.is_dragging = False
        return was_click

    def center_and_resize(self, window, parent=None):
        """
        Calcula el tamaño necesario para el contenido y centra la ventana.
        """
        # Ocultar ventana mientras se calcula para evitar parpadeos
        window.withdraw()
        window.update_idletasks()  # Forzar cálculo de dimensiones
        
        # Obtener tamaño requerido por los widgets + un poco de padding
        req_w = window.winfo_reqwidth() + 20
        req_h = window.winfo_reqheight() + 20
        
        # Obtener dimensiones de pantalla
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        
        # Calcular posición centrada
        x = int((screen_w / 2) - (req_w / 2))
        y = int((screen_h / 2) - (req_h / 2))
        
        # Aplicar geometría
        window.geometry(f"{req_w}x{req_h}+{x}+{y}")
        window.deiconify()  # Mostrar ventana

    def elevate(self, window, parent=None):
        """
        Fuerza a 'window' a mostrarse por encima de otras ventanas de la app.

        Cada paso va en su propio try/except: en Linux hay mucha variedad de
        WM/compositores y no todos soportan los mismos hints (por ejemplo
        '-type dialog' es X11 puro, puede fallar bajo Wayland). Si alguno
        falla no debe frenar la creación del diálogo ni dejarlo a medio
        inicializar con un grab_set() colgado.
        """
        if parent is not None:
            try:
                window.transient(parent)
            except Exception:
                pass

        try:
            window.attributes('-topmost', True)
        except Exception:
            pass

        if sys.platform.startswith('linux'):
            try:
                window.attributes('-type', 'dialog')
            except Exception:
                pass

        try:
            window.lift()
            window.focus_force()
        except Exception:
            pass

        for delay in (10, 60, 150):
            try:
                window.after(delay, window.lift)
            except Exception:
                pass

    def safe_grab_set(self, window):
        """
        grab_set() falla con TclError si la ventana todavía no es 'viewable'
        (puede pasar justo después de deiconify() en algunos WM). En vez de
        dejar la excepción sin capturar -lo que deja el diálogo abierto pero
        sin inputs- reintenta una vez en el próximo ciclo de eventos.
        """
        try:
            window.grab_set()
        except Exception:
            window.after(50, lambda: window.grab_set() if window.winfo_exists() else None)