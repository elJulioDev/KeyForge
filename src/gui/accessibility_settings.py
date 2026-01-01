"""
Componente de configuración de accesibilidad (Idioma y Tema)
"""
import ttkbootstrap as ttk
from tkinter import StringVar


class AccessibilityComponent:
    """Componente para configurar idioma y tema de la aplicación"""
    
    # Temas disponibles en ttkbootstrap
    AVAILABLE_THEMES = [
        # Temas Claros (Light)
        "cosmo", "flatly", "journal", "litera", "lumen", 
        "minty", "pulse", "sandstone", "united", "yeti", 
        "morph", "simplex", "cerculean",
        
        # Temas Oscuros (Dark)
        "cyborg", "darkly", "solar", "superhero", "vapor"
    ]
    
    # Mapeo de códigos de idioma a nombres completos
    LANGUAGE_NAMES = {
        "es": {"es": "Español", "en": "Spanish"},
        "en": {"es": "Inglés", "en": "English"}
    }
    
    def __init__(self, parent, tr, current_lang, current_theme, on_change_callback):
        """
        Args:
            parent: Widget padre
            tr: Diccionario de traducciones
            current_lang: Idioma actual (código: 'es', 'en')
            current_theme: Tema actual
            on_change_callback: Función a llamar cuando cambia idioma o tema
        """
        self.parent = parent
        self.tr = tr
        self.on_change = on_change_callback
        
        self.lang_var = StringVar(value=current_lang)
        display_theme_name = self._get_display_name_from_code(current_theme)
        self.theme_var = StringVar(value=display_theme_name)
        
        self._create_ui()
    
    def _create_ui(self):
        """Crea la interfaz del componente"""
        # Frame principal
        self.frame = ttk.Frame(self.parent, padding=20)
        self.frame.pack(fill="both", expand=True)
        
        # Título
        title = ttk.Label(
            self.frame,
            text=self.tr.get("accessibility_title", "♿ Accessibility"),
            font=("-size", 14, "-weight", "bold")
        )
        title.pack(pady=(0, 20))
        
        # --- SECCIÓN IDIOMA ---
        lang_frame = ttk.Labelframe(
            self.frame,
            text=self.tr.get("language_label", "Language:"),
            padding=15
        )
        lang_frame.pack(fill="x", pady=(0, 15))
        
        # Obtener idioma actual para mostrar nombres correctos
        current_lang = self.lang_var.get()
        
        # Radio buttons para idiomas
        for lang_code in ["es", "en"]:
            lang_display_name = self.LANGUAGE_NAMES[lang_code][current_lang]
            
            ttk.Radiobutton(
                lang_frame,
                text=f"{'🇪🇸' if lang_code == 'es' else '🇬🇧'} {lang_display_name}",
                variable=self.lang_var,
                value=lang_code,
                command=self._on_language_change,
                bootstyle="primary"
            ).pack(anchor="w", pady=5)
        
        # --- SECCIÓN TEMA ---
        theme_frame = ttk.Labelframe(
            self.frame,
            text=self.tr.get("theme_label", "Theme:"),
            padding=15
        )
        theme_frame.pack(fill="x", pady=(0, 15))
        
        # Combobox para temas
        self.theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=self._get_translated_themes(),
            state="readonly",
            width=30
        )
        self.theme_combo.pack(fill="x", pady=5)
        self.theme_combo.bind("<<ComboboxSelected>>", lambda e: self._on_theme_change())
                
        # Info
        ttk.Separator(self.frame).pack(fill="x", pady=15)
        
        info_label = ttk.Label(
            self.frame,
            text=self.tr.get("accessibility_info", "⚠️ The application will restart to apply changes"),
            font=("-size", 9)
        )
        info_label.pack()
    
    def _get_translated_themes(self):
        """Retorna lista de temas (Nombres originales capitalizados)"""
        # Simplemente capitalizamos el nombre: 'darkly' -> 'Darkly'
        return [theme.capitalize() for theme in self.AVAILABLE_THEMES]
    
    def _get_theme_code_from_display(self, display_name):
        """Convierte nombre mostrado a código de tema"""
        # Inverso: 'Darkly' -> 'darkly'
        return display_name.lower()
    
    def _on_language_change(self):
        """Callback cuando cambia el idioma"""
        new_lang = self.lang_var.get()
        if self.on_change:
            self.on_change("lang", new_lang)
    
    def _on_theme_change(self):
        """Callback cuando cambia el tema"""
        display_name = self.theme_var.get()
        theme_code = self._get_theme_code_from_display(display_name)
        if self.on_change:
            self.on_change("theme", theme_code)
    
    def get_current_settings(self):
        """Retorna configuración actual"""
        display_name = self.theme_var.get()
        theme_code = self._get_theme_code_from_display(display_name)
        
        return {
            "lang": self.lang_var.get(),
            "theme": theme_code
        }
    
    def _get_display_name_from_code(self, theme_code):
        """Devuelve el nombre para mostrar dado un código"""
        # 'darkly' -> 'Darkly'
        return theme_code.capitalize()