"""
Accessibility settings component (Language, Theme and Updates)
"""
import threading
import ttkbootstrap as ttk
from tkinter import StringVar
from tkinter.messagebox import askyesno, showinfo, showerror
from src.utils.auto_updater import AutoUpdater

class AccessibilityComponent:
    """Component for configuring language, theme and updates"""
    
    # Themes available in ttkbootstrap
    AVAILABLE_THEMES = [
        # Light Themes
        "cosmo", "flatly", "journal", "litera", "lumen", 
        "minty", "pulse", "sandstone", "united", "yeti", 
        "morph", "simplex", "cerculean",
        
        # Dark Themes
        "cyborg", "darkly", "solar", "superhero", "vapor"
    ]
    
    def __init__(self, parent, tr_manager, current_lang, current_theme, on_change_callback):
        """
        Args:
            parent: Parent widget
            tr_manager: TranslationManager instance
            current_lang: Current language (code: 'es', 'en')
            current_theme: Current theme
            on_change_callback: Function called when language or theme changes
        """
        self.parent = parent
        self.tr_manager = tr_manager
        self.tr = tr_manager
        self.on_change = on_change_callback
        
        self.lang_var = StringVar(value=current_lang)
        display_theme_name = self._get_display_name_from_code(current_theme)
        self.theme_var = StringVar(value=display_theme_name)
        
        # Track the currently applied values so re-selecting the SAME
        # value (theme/language) does not trigger a save/restart.
        self._applied_lang = current_lang
        self._applied_theme = current_theme
        
        self.updater = AutoUpdater() # Updater instance
        
        self._create_ui()
    
    def _create_ui(self):
        """Creates the component interface"""
        # Main frame
        self.frame = ttk.Frame(self.parent, padding=20)
        self.frame.pack(fill="both", expand=True)
        
        # --- LANGUAGE SECTION ---
        self.lang_frame = ttk.Labelframe(
            self.frame,
            text=self.tr("language_label"),
            padding=15
        )
        self.lang_frame.pack(fill="x", pady=(0, 15))
        
        # Radio buttons for languages (generated dynamically)
        self._create_language_radios()
        
        # --- THEME SECTION ---
        self.theme_frame = ttk.Labelframe(
            self.frame,
            text=self.tr("theme_label"),
            padding=15
        )
        self.theme_frame.pack(fill="x", pady=(0, 15))
        
        # Combobox for themes
        self.theme_combo = ttk.Combobox(
            self.theme_frame,
            textvariable=self.theme_var,
            values=self._get_translated_themes(),
            state="readonly",
            width=30
        )
        self.theme_combo.pack(fill="x", pady=5)
        self.theme_combo.bind("<<ComboboxSelected>>", lambda e: self._on_theme_change())

        # --- UPDATES SECTION ---
        self.update_frame = ttk.Labelframe(
            self.frame,
            text=self.tr("updates_title"),
            padding=15
        )
        self.update_frame.pack(fill="x", pady=(0, 15))

        self.check_btn = ttk.Button(
            self.update_frame,
            text=self.tr("check_updates_btn"),
            command=self._check_updates,
            bootstyle="primary",
            width=25
        )
        self.check_btn.pack()
    
    def _create_language_radios(self):
        """Creates language radio buttons dynamically from meta"""
        languages = self.tr_manager.get_available_languages()
        
        for lang_code in languages.keys():
            lang_display_name = self.tr_manager.get_language_name(
                lang_code, self.tr_manager.current_lang
            )
            
            ttk.Radiobutton(
                self.lang_frame,
                text=lang_display_name,
                variable=self.lang_var,
                value=lang_code,
                command=self._on_language_change,
                bootstyle="primary"
            ).pack(anchor="w", pady=5)
    
    def _check_updates(self):
        """Logic for the check updates button (runs the HTTP request off the UI thread)"""
        original_text = self.check_btn.cget("text")
        self.check_btn.configure(text=self.tr("checking_updates"), state="disabled")
        self.frame.update() # Force UI refresh

        def worker():
            has_update, data = self.updater.check_for_updates()
            # Marshal back to the Tk main thread
            self.frame.after(0, lambda: self._on_check_done(
                original_text, has_update, data))

        threading.Thread(target=worker, daemon=True).start()

    def _on_check_done(self, original_text, has_update, data):
        """Re-enables the button and shows the result (main thread)."""
        try:
            self.check_btn.configure(text=original_text, state="normal")
        except Exception:
            return  # widget destroyed while the request was in flight

        if has_update:
            # Data is a dict with {version, url, body}
            msg = self.tr("update_available_msg", version=data['version'])
            if askyesno(self.tr("update_available_title"), msg):
                self.updater.open_download_page(data['url'])
        else:
            # Data is the current version string or an error message
            if "error" in str(data).lower() or "exception" in str(data).lower():
                showerror(self.tr("error_title"), self.tr("update_error_msg"))
            else:
                showinfo(self.tr("title"), self.tr("no_update_msg", version=data))
    
    def _get_translated_themes(self):
        """Returns list of themes (original names capitalized)"""
        return [theme.capitalize() for theme in self.AVAILABLE_THEMES]
    
    def _get_theme_code_from_display(self, display_name):
        """Converts displayed name to theme code"""
        return display_name.lower()
    
    def _on_language_change(self):
        """Callback when the language changes"""
        new_lang = self.lang_var.get()
        # Re-selecting the already-applied language is a no-op
        if new_lang == self._applied_lang:
            return
        self._applied_lang = new_lang
        if self.on_change:
            self.on_change("lang", new_lang)
    
    def _on_theme_change(self):
        """Callback when the theme changes"""
        display_name = self.theme_var.get()
        theme_code = self._get_theme_code_from_display(display_name)
        # Re-selecting the already-applied theme must not restart the app
        if theme_code == self._applied_theme:
            return
        self._applied_theme = theme_code
        if self.on_change:
            self.on_change("theme", theme_code)
    
    def get_current_settings(self):
        """Returns the current settings"""
        display_name = self.theme_var.get()
        theme_code = self._get_theme_code_from_display(display_name)
        
        return {
            "lang": self.lang_var.get(),
            "theme": theme_code
        }
    
    def _get_display_name_from_code(self, theme_code):
        """Returns the display name given a code"""
        return theme_code.capitalize()
    
    def update_translations(self):
        """Updates the component translations"""
        # Sections
        self.lang_frame.config(text=self.tr("language_label"))
        self.theme_frame.config(text=self.tr("theme_label"))
        self.update_frame.config(text=self.tr("updates_title"))
        
        # Updates button
        self.check_btn.config(text=self.tr("check_updates_btn"))
        
        # Recreate language radio buttons with names in the new language
        for child in self.lang_frame.winfo_children():
            child.destroy()
        self._create_language_radios()
