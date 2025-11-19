"""
Monitor de ventanas basado en eventos (Windows-only)
Alternativa eficiente al polling
"""

import sys
import threading

# Importar solo en Windows
if sys.platform == 'win32':
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        ole32 = ctypes.windll.ole32
        
        # Constantes de WinEvent
        WINEVENT_OUTOFCONTEXT = 0x0000
        EVENT_SYSTEM_FOREGROUND = 0x0003
        
        # Definir tipo de callback
        WinEventProcType = ctypes.WINFUNCTYPE(
            None,
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.HWND,
            wintypes.LONG,
            wintypes.LONG,
            wintypes.DWORD,
            wintypes.DWORD
        )
        
        WINDOWS_EVENTS_AVAILABLE = True
    except Exception:
        WINDOWS_EVENTS_AVAILABLE = False
else:
    WINDOWS_EVENTS_AVAILABLE = False


class WindowEventMonitor:
    """
    Monitor de cambios de ventana usando WinEventHook (solo Windows).
    Más eficiente que polling porque solo reacciona cuando cambia el foco.
    """
    
    def __init__(self, callback=None):
        """
        Args:
            callback: Función que se llama cuando cambia la ventana activa
                      Recibe (window_title: str) como parámetro
        """
        self.callback = callback
        self.hook_handle = None
        self.running = False
        self.thread = None
        self._callback_ref = None  # Mantener referencia para evitar GC
        
        if not WINDOWS_EVENTS_AVAILABLE:
            raise RuntimeError("WinEventHook no disponible en este sistema")
    
    def start(self):
        """Inicia el monitor de eventos"""
        if self.running:
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._event_loop, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        """Detiene el monitor de eventos"""
        if not self.running:
            return False
        
        self.running = False
        if self.hook_handle:
            user32.UnhookWinEvent(self.hook_handle)
            self.hook_handle = None
        
        if self.thread:
            self.thread.join(timeout=1)
        
        return True
    
    def _event_loop(self):
        """Loop principal de eventos (ejecutado en thread separado)"""
        # Definir el callback que se llamará en cada evento
        def win_event_callback(hWinEventHook, event, hwnd, idObject, idChild, 
                              dwEventThread, dwmsEventTime):
            # Solo procesar cambios de ventana en primer plano
            if event == EVENT_SYSTEM_FOREGROUND:
                window_title = self._get_window_title(hwnd)
                if window_title and self.callback:
                    # Llamar al callback en el thread principal (thread-safe)
                    self.callback(window_title)
        
        # Mantener referencia para evitar garbage collection
        self._callback_ref = WinEventProcType(win_event_callback)
        
        # Registrar el hook
        self.hook_handle = user32.SetWinEventHook(
            EVENT_SYSTEM_FOREGROUND,  # eventMin
            EVENT_SYSTEM_FOREGROUND,  # eventMax
            0,                         # hmodWinEventProc
            self._callback_ref,        # callback
            0,                         # idProcess (0 = todos)
            0,                         # idThread (0 = todos)
            WINEVENT_OUTOFCONTEXT      # dwFlags
        )
        
        if not self.hook_handle:
            print("❌ Error: No se pudo registrar WinEventHook")
            self.running = False
            return
        
        # Loop de mensajes de Windows
        msg = wintypes.MSG()
        while self.running:
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == 0 or result == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    
    @staticmethod
    def _get_window_title(hwnd):
        """Obtiene el título de una ventana por handle"""
        try:
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return ""
            
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            return buffer.value
        except Exception:
            return ""


# Función de utilidad para verificar disponibilidad
def is_event_monitoring_available():
    """Verifica si el monitoreo por eventos está disponible"""
    return WINDOWS_EVENTS_AVAILABLE
