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
            print(f"Error al obtener ventanas: {e}")
            return []

    def use_event_monitoring(self, callback):
        """
        Activa monitoreo basado en eventos (solo Windows).
        
        Args:
            callback: Función que se llama cuando cambia la ventana activa
        
        Returns:
            True si se activó correctamente, False si no está disponible
        """
        try:
            from .window_event_monitor import WindowEventMonitor, is_event_monitoring_available
            
            if not is_event_monitoring_available():
                return False
            
            def on_window_change(window_title):
                # Actualizar estado cuando cambia la ventana
                if self.target_app_name.lower() in window_title.lower():
                    self.target_app_is_active = True
                else:
                    self.target_app_is_active = False
                
                # Llamar callback externo
                if callback:
                    callback(self.target_app_is_active)
            
            self.event_monitor = WindowEventMonitor(on_window_change)
            self.event_monitor.start()
            return True
            
        except Exception as e:
            print(f"⚠️ Event monitoring no disponible: {e}")
            return False
    
    def stop_event_monitoring(self):
        """Detiene el monitoreo por eventos"""
        if hasattr(self, 'event_monitor'):
            self.event_monitor.stop()