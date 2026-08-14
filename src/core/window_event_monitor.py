"""
Event-based window monitor (Windows-only)
Efficient alternative to polling
"""

import sys
import threading

# Import only on Windows
if sys.platform == 'win32':
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        ole32 = ctypes.windll.ole32
        
        # WinEvent constants
        WINEVENT_OUTOFCONTEXT = 0x0000
        EVENT_SYSTEM_FOREGROUND = 0x0003
        
        # Define callback type
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
    Window change monitor using WinEventHook (Windows only).
    More efficient than polling because it only reacts when focus changes.
    """
    
    def __init__(self, callback=None):
        """
        Args:
            callback: Function called when the active window changes
                      Receives (window_title: str) as a parameter
        """
        self.callback = callback
        self.hook_handle = None
        self.running = False
        self.thread = None
        self._thread_id = None
        self._callback_ref = None  # Keep a reference to avoid GC
        
        if not WINDOWS_EVENTS_AVAILABLE:
            raise RuntimeError("WinEventHook not available on this system")
    
    def start(self):
        """Start the event monitor"""
        if self.running:
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._event_loop, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        """Stop the event monitor"""
        if not self.running:
            return False
        
        self.running = False
        if self.hook_handle:
            user32.UnhookWinEvent(self.hook_handle)
            self.hook_handle = None
        
        # GetMessageW blocks until a message arrives; setting running=False is
        # not enough to wake it. Post WM_QUIT (0x0012) to break the loop so
        # the thread actually exits instead of leaking on every start/stop.
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        
        if self.thread:
            self.thread.join(timeout=1)
        
        return True
    
    def _event_loop(self):
        """Main event loop (runs in a separate thread)"""
        self._thread_id = threading.get_ident()
        # Define the callback that will be called on each event
        def win_event_callback(hWinEventHook, event, hwnd, idObject, idChild, 
                              dwEventThread, dwmsEventTime):
            # Only process foreground window changes
            if event == EVENT_SYSTEM_FOREGROUND:
                window_title = self._get_window_title(hwnd)
                if window_title and self.callback:
                    # Call the callback in the main thread (thread-safe)
                    self.callback(window_title)
        
        # Keep a reference to avoid garbage collection
        self._callback_ref = WinEventProcType(win_event_callback)
        
        # Register the hook
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
            print("Error: Could not register WinEventHook")
            self.running = False
            return
        
        # Windows message loop
        msg = wintypes.MSG()
        while self.running:
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == 0 or result == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    
    @staticmethod
    def _get_window_title(hwnd):
        """Get a window's title by handle"""
        try:
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return ""
            
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            return buffer.value
        except Exception:
            return ""


# Utility function to check availability
def is_event_monitoring_available():
    """Check if event monitoring is available"""
    return WINDOWS_EVENTS_AVAILABLE
