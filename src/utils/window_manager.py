"""
Utilities for window management.
"""
import sys


class WindowManager:
    """Handles window operations such as dragging and dynamic centering."""

    def __init__(self):
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.offset_x = 0
        self.offset_y = 0
    
    def start_drag(self, event, window):
        """Start dragging a window."""
        self.offset_x = event.x_root - window.winfo_x()
        self.offset_y = event.y_root - window.winfo_y()
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.is_dragging = False
    
    def drag(self, event, window):
        """Drag the window following the mouse."""
        x = event.x_root - self.offset_x
        y = event.y_root - self.offset_y
        window.geometry(f"+{x}+{y}")
        self.is_dragging = True
    
    def end_drag(self, event):
        """End the drag and detect whether it was a click or a drag."""
        distance = abs(event.x_root - self.drag_start_x) + abs(event.y_root - self.drag_start_y)
        was_click = distance < 5 and not self.is_dragging
        self.is_dragging = False
        return was_click

    def center_and_resize(self, window, parent=None):
        """
        Calculate the size needed for the content and center the window.
        """
        # Hide the window while calculating to avoid flicker
        window.withdraw()
        window.update_idletasks()  # Force dimension calculation
        
        # Get the size required by the widgets + a bit of padding
        req_w = window.winfo_reqwidth() + 20
        req_h = window.winfo_reqheight() + 20
        
        # Get screen dimensions
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        
        # Calculate centered position
        x = int((screen_w / 2) - (req_w / 2))
        y = int((screen_h / 2) - (req_h / 2))
        
        # Apply geometry
        window.geometry(f"{req_w}x{req_h}+{x}+{y}")
        window.deiconify()  # Show window

    def elevate(self, window, parent=None):
        """
        Force 'window' to show above the other windows of the app.

        Each step goes in its own try/except: on Linux there is a lot of
        variety of WM/compositors and not all of them support the same hints
        (for example '-type dialog' is pure X11, it can fail under Wayland).
        If any of them fails it must not stop the dialog creation nor leave
        it half-initialized with a stuck grab_set().
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
        grab_set() fails with TclError if the window is not 'viewable' yet
        (this can happen right after deiconify() on some WMs). Instead of
        leaving the exception uncaught - which leaves the dialog open but
        without inputs - retry once on the next event loop cycle.
        """
        try:
            window.grab_set()
        except Exception:
            window.after(50, lambda: window.grab_set() if window.winfo_exists() else None)