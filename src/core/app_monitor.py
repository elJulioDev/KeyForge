"""
Monitor de aplicaciones activas
"""
import pygetwindow as gw


class AppMonitor:
    """Monitorea si la aplicación objetivo está activa"""
    
    def __init__(self):
        self.target_app_name = ""
        self.enforce_app_focus = True
        self.target_app_is_active = False
    
    def set_target_app(self, app_name):
        """Establece la aplicación objetivo"""
        self.target_app_name = app_name
    
    def set_enforce_focus(self, enforce):
        """Activa o desactiva el enfoque en aplicación específica"""
        self.enforce_app_focus = enforce
    
    def is_target_app_active(self):
        """
        Verifica si la ventana activa coincide con la aplicación objetivo.
        Si enforce_app_focus es False, siempre retorna True (funciona globalmente).
        """
        if not self.enforce_app_focus:
            return True
        
        try:
            active_window = gw.getActiveWindow()
            if active_window and self.target_app_name.lower() in active_window.title.lower():
                return True
        except Exception:
            pass
        
        return False
    
    def update_status(self):
        """Actualiza el estado de detección de la app"""
        self.target_app_is_active = self.is_target_app_active()
        return self.target_app_is_active
    
    @staticmethod
    def get_all_windows():
        """Obtiene lista de todas las ventanas abiertas"""
        try:
            all_windows = gw.getAllTitles()
            # Filtrar ventanas vacías y duplicados
            unique_windows = []
            seen = set()
            for window in all_windows:
                if window.strip() and window not in seen:
                    unique_windows.append(window)
                    seen.add(window)
            return unique_windows
        except Exception as e:
            print(f"❌ Error al obtener ventanas: {e}")
            return []
