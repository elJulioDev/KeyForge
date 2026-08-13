"""
Floating minimized window
"""
import ttkbootstrap as ttk
from ..utils.window_manager import WindowManager
from ..utils.icons import get_icon


class MinimizedWindow:
    """Minimalist floating window for the minimized state"""
    
    def __init__(self, parent, on_restore_callback, on_toggle_callback):
        """Initialize the minimized window."""
        self.parent = parent
        self.on_restore = on_restore_callback
        self.on_toggle = on_toggle_callback  # We store the toggle function
        self.window = None
        self.window_manager = WindowManager()
        self.canvas = None # Canvas reference to redraw
        self.size = 90     # Stored size
    
    def show(self, is_active=False, center_pos=None):
        """Shows the minimized window with the corresponding visual state"""
        if self.window:
            return
        
        # GET CURRENT THEME COLORS
        style = ttk.Style()
        theme_bg = style.colors.bg
        
        # Create floating window
        self.window = ttk.Toplevel(self.parent)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.0) # Starts invisible for fade-in
        
        # Size
        size = 90
        
        # POSITION CALCULATION
        if center_pos:
            # If we are given the center of the main window, we center there
            cx, cy = center_pos
            x_pos = int(cx - (size / 2))
            y_pos = int(cy - (size / 2))
        else:
            # Fallback: Centered on screen (previous behavior)
            screen_w = self.parent.winfo_screenwidth()
            screen_h = self.parent.winfo_screenheight()
            x_pos = int((screen_w / 2) - (size / 2))
            y_pos = int((screen_h / 2) - (size / 2))
        
        self.window.geometry(f"{size}x{size}+{x_pos}+{y_pos}")
        
        # APPLY THEME BACKGROUND
        self.window.configure(background=theme_bg)
        
        self.canvas = ttk.Canvas(
            self.window,
            width=self.size,
            height=self.size,
            highlightthickness=0,
            bg=theme_bg
        )
        self.canvas.pack(fill="both", expand=True)
        
        # WE PASS THE STATE TO THE DRAWING
        self._draw_pro_icon(self.canvas, size, is_active)
        
        # Events
        self._bind_events(self.canvas)
        
        # Entrance animation
        self._fade_in()
    
    def update_visuals(self, is_active):
        """Redraws the icon according to the new state (Active/Inactive)"""
        if self.canvas:
            self.canvas.delete("all") # Clears the previous drawing
            self._draw_pro_icon(self.canvas, self.size, is_active)

    def _draw_pro_icon(self, canvas, s, is_active):
        """
        Draws a modern icon using the theme colors.
        """
        # 3. GET THE THEME COLOR PALETTE
        style = ttk.Style()
        colors = style.colors
        
        pad = 5
        r = 16 
        
        bg_color = colors.bg
        
        # DYNAMIC COLOR LOGIC
        if is_active:
            # ACTIVE STATE: Bright colors
            accent_color = colors.success  # Green border (or theme success color)
            icon_color = colors.fg         # Icon main color (text)
            dot_color = colors.success     # LED on
            key_fill = colors.secondary    # Key body
            key_border = colors.border     # Standard border
        else:
            # INACTIVE STATE: Dimmed colors
            accent_color = colors.secondary
            icon_color = colors.secondary  # Grayish icon (secondary)
            dot_color = colors.dark        # LED off
            key_fill = colors.inputbg      # "Input" type background (empty text box)
            key_border = colors.border     # Standard border
            
        # Outer border (Glow/Frame)
        self._round_rect(canvas, pad, pad, s-pad, s-pad, r, outline=accent_color, width=2, fill=bg_color)
        
        # Representation of a Key
        k_pad = 22
        
        # Key shadow (we use colors.dark for depth)
        self._round_rect(canvas, k_pad, k_pad-2, s-k_pad, s-k_pad-2, 8, fill=colors.dark, outline="") 
        
        # Key face (Uses dynamic color)
        self._round_rect(canvas, k_pad, k_pad, s-k_pad, s-k_pad, 8, fill=key_fill, outline=key_border, width=1) 
        
        # Icon (Uses dynamic color)
        wrench_icon = get_icon("wrench", 36, icon_color)
        canvas.create_image(s/2, s/2, image=wrench_icon)
        
        # State indicator (LED)
        ind_r = 3
        ind_x = s - 15
        ind_y = 15
        canvas.create_oval(ind_x-ind_r, ind_y-ind_r, ind_x+ind_r, ind_y+ind_r, fill=dot_color, outline="")

    def _round_rect(self, canvas, x1, y1, x2, y2, radius=25, **kwargs):
        """Helper function to draw rounded rectangles"""
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
        """Configures drag and click events"""
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
        """Restores the main window passing the current position"""
        if self.window:
            # 1. Get the current center of the minimized window
            mx = self.window.winfo_x()
            my = self.window.winfo_y()
            mw = self.window.winfo_width()
            mh = self.window.winfo_height()
            
            center_x = mx + (mw / 2)
            center_y = my + (mh / 2)
            
            # We hide the icon
            self.hide()
            
            # 2. We call the callback passing the position (center_pos)
            # Note: self.on_restore is _restore_window in the main app
            self.on_restore(center_pos=(center_x, center_y))
        else:
            self.on_restore()

    def _fade_in(self, alpha=0.0):
        """Fades the window in by gradually increasing the alpha."""
        if self.window and alpha < 0.9:
            self.window.attributes('-alpha', alpha)
            self.parent.after(15, lambda: self._fade_in(alpha + 0.05))
    
    def hide(self):
        """Destroys the minimized window."""
        if self.window:
            self.window.destroy()
            self.window = None
            self.canvas = None
    
    def is_visible(self):
        """Returns whether the minimized window is currently visible."""
        return self.window is not None