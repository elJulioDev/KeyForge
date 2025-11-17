"""
Utilidades para manejo de ventanas
"""


class WindowManager:
    """Gestiona operaciones de ventanas como arrastre"""
    
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
