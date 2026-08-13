"""
src/gui/splash_screen.py
Dynamic Splash Screen for KeyForge
Automatically adapts to light and dark themes and supports translation.
"""
import ttkbootstrap as ttk
from tkinter import Canvas
from ..utils.icons import get_icon

class SplashScreen:
    """
    Minimalist splash screen that respects the application theme.
    """
    
    def __init__(self, parent_root, tr_manager=None, title="KeyForge", version="1.0"):
        """Initialize and show the splash screen."""
        self.root = parent_root
        self.tr = tr_manager
        self.title_text = title
        self.version_text = f"v{version}"
        
        # 1. Get the style and colors of the current theme
        self.style = ttk.Style()
        self.colors = self.style.colors
        
        self.window = None
        self.canvas = None
        self.progress_value = 0
        
        self._show()

    def _is_light_theme(self):
        """Detects if the current theme is light"""
        return self.style.theme.type == 'light'

    def _show(self):
        """Initializes and shows the window"""
        self.window = ttk.Toplevel(self.root)
        self.window.overrideredirect(True) # No borders
        self.window.attributes('-topmost', True)
        
        # Compact dimensions
        width = 360
        height = 160
        
        # Center on screen
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 2. Use the theme background color (bg) instead of a fixed black
        bg_color = self.colors.bg 
        self.window.configure(bg=bg_color)
        
        # Canvas also uses the theme background
        self.canvas = Canvas(
            self.window,
            width=width,
            height=height,
            bg=bg_color,
            highlightthickness=0
        )
        self.canvas.pack(fill='both', expand=True)
        
        self._draw_ui(width, height)
        self.window.update()

    def _draw_ui(self, w, h):
        """Draws the elements using dynamic colors"""
        
        # Colors extracted from the theme
        fg_color = self.colors.fg            
        secondary_color = self.colors.secondary  
        border_color = self.colors.border    
        accent_color = self.colors.success   
        
        # Progress bar background
        if self._is_light_theme():
            bar_bg_color = "#e0e0e0" 
        else:
            bar_bg_color = "#111111" 

        # --- BORDERS ---
        self.canvas.create_rectangle(
            0, 0, w-1, h-1,
            outline=border_color,
            width=1
        )
        
        # --- TITLE (Adaptive color) ---
        title_icon = get_icon("wrench", 26, fg_color)
        self.canvas.create_image(w//2 - 62, 50, image=title_icon, anchor="e")
        self.canvas.title_icon = title_icon  # live reference
        self.canvas.create_text(
            w//2 - 50, 50,
            text=self.title_text,
            font=("Segoe UI", 18, "bold"),
            fill=fg_color,
            anchor="w"
        )
        
        # --- VERSION ---
        self.canvas.create_text(
            w//2, 90,
            text=self.version_text,
            font=("Segoe UI", 8),
            fill=secondary_color,
            anchor="center"
        )
        
        # --- PROGRESS BAR ---
        bar_y = 105
        bar_height = 6
        
        # Bar background
        self.progress_bg = self.canvas.create_rectangle(
            50, bar_y, w-50, bar_y + bar_height,
            fill=bar_bg_color,
            outline=border_color,
            width=1
        )
        
        # Bar fill (Accent/Success color)
        self.progress_bar = self.canvas.create_rectangle(
            50, bar_y, 50, bar_y + bar_height, 
            fill=accent_color,
            outline="",
            tags="progress"
        )
        
        # --- STATUS INFORMATION ---
        initial_text = self.tr.tr("splash_init") if self.tr else "Initializing..."
        self.status_text_id = self.canvas.create_text(
            50, bar_y + 20,
            text=initial_text,
            font=("Segoe UI", 8),
            fill=secondary_color,
            anchor="w"
        )
        
        # Right side: Percentage
        self.percent_text = self.canvas.create_text(
            w-50, bar_y + 20,
            text="0%",
            font=("Segoe UI", 8, "bold"),
            fill=accent_color,
            anchor="e"
        )

    def update_step(self, value, text):
        """Updates the display"""
        if not self.canvas: return
        
        self.progress_value = max(0, min(100, value))
        
        # Geometry calculation
        w = 360
        margin = 50
        max_bar_width = w - (margin * 2)
        current_width = max_bar_width * (self.progress_value / 100)
        
        bar_y = 105
        bar_height = 6
        
        self.canvas.coords(
            self.progress_bar, 
            margin, bar_y, 
            margin + current_width, bar_y + bar_height
        )
        
        # We use the theme success color for consistency
        fill_color = self.colors.success
            
        self.canvas.itemconfig(self.progress_bar, fill=fill_color)
        
        # Texts
        self.canvas.itemconfig(self.percent_text, text=f"{int(self.progress_value)}%")
        self.canvas.itemconfig(self.status_text_id, text=text)
        
        self.window.update_idletasks()

    def close(self):
        """Closes the splash"""
        if self.window:
            self.window.destroy()
            self.window = None