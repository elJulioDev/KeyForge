"""
Translation manager with hot-reload support
"""
import json
from pathlib import Path


class TranslationManager:
    """
    Manages translations with hot-reload support.
    
    Expected lang.json structure:
    {
        "meta": {
            "es": {"name": "Español", "native": "Español"},
            "en": {"name": "English", "native": "English"}
        },
        "translations": {
            "es": { ... },
            "en": { ... }
        }
    }
    """
    
    def __init__(self, lang_file_path):
        """
        Args:
            lang_file_path: Path to the lang.json file
        """
        self.lang_file = Path(lang_file_path)
        self._translations = {}  # {lang_code: {key: value}}
        self._meta = {}          # {lang_code: {name, native}}
        self.current_lang = "en"
        self._subscribers = []   # Components subscribed to changes
        self._is_updating = False  # Guard against re-entrancy
        
    def load(self):
        """Loads lang.json with improved structure"""
        try:
            if not self.lang_file.exists():
                print(f"Translations file not found: {self.lang_file}")
                return False
                
            with open(self.lang_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Support for new structure (meta + translations)
            if "translations" in data:
                self._translations = data["translations"]
                self._meta = data.get("meta", {})
            else:
                # Fallback: old structure (translations only)
                self._translations = data
                self._meta = {}
            
            print(f"Translations loaded: {list(self._translations.keys())}")
            return True
            
        except Exception as e:
            print(f"Error loading translations: {e}")
            self._translations = {"es": {}, "en": {}}
            return False
    
    def tr(self, key, **kwargs):
        """
        Translates a key with fallback chain: current → english → key
        
        Args:
            key: Translation key
            **kwargs: Parameters for format() (e.g.: app="MyApp")
            
        Returns:
            str: Translated text or key if it does not exist
        """
        # 1. Search in the current language
        text = self._translations.get(self.current_lang, {}).get(key)
        
        # 2. Fallback to English
        if text is None:
            text = self._translations.get("en", {}).get(key)
        
        # 3. Fallback to the key itself
        if text is None:
            text = key
        
        # 4. Apply format if there are kwargs
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass  # If a parameter is missing, return without formatting
        
        return text
    
    def __call__(self, key, **kwargs):
        """Allows direct call: tr("key", app="X")"""
        return self.tr(key, **kwargs)
    
    def get_available_languages(self):
        """
        Returns a dictionary of available languages from meta.
        
        Returns:
            dict: {code: {name, native}} or empty dict if there is no meta
        """
        if self._meta:
            return self._meta.copy()
        
        # Fallback: generate from available translations
        return {lang: {"name": lang.upper(), "native": lang.upper()} 
                for lang in self._translations.keys()}
    
    def get_language_name(self, lang_code, display_lang=None):
        """
        Returns the language name for the UI.
        
        Args:
            lang_code: Language code (e.g.: "es")
            display_lang: Language in which to show the name (default: current language)
            
        Returns:
            str: Language name
        """
        if display_lang is None:
            display_lang = self.current_lang
        
        # Search in meta
        if lang_code in self._meta:
            lang_info = self._meta[lang_code]
            return lang_info.get(display_lang, lang_info.get("native", lang_code))
        
        return lang_code.upper()
    
    def set_language(self, lang_code):
        """
        Changes the language and notifies subscribers.
        
        Args:
            lang_code: New language code
            
        Returns:
            bool: True if the language changed, False if it was the same
        """
        if lang_code == self.current_lang:
            return False
            
        if lang_code not in self._translations:
            print(f"Language not available: {lang_code}")
            return False
        
        old_lang = self.current_lang
        self.current_lang = lang_code
        
        print(f"Language changed: {old_lang} → {lang_code}")
        self._notify_subscribers()
        return True
    
    def subscribe(self, component):
        """
        Registers a component for language change notifications.
        
        Args:
            component: Instance with an update_translations() method
        """
        if component not in self._subscribers:
            self._subscribers.append(component)
    
    def unsubscribe(self, component):
        """
        Removes a component from the subscribers.
        
        Args:
            component: Instance to remove
        """
        try:
            self._subscribers.remove(component)
        except ValueError:
            pass
    
    def _notify_subscribers(self):
        """Calls update_translations() on all subscribers"""
        if self._is_updating:
            return  # Prevent re-entrancy
        
        self._is_updating = True
        try:
            for component in self._subscribers[:]:  # Copy to avoid modification
                try:
                    component.update_translations()
                except Exception as e:
                    print(f"Error updating component: {e}")
        finally:
            self._is_updating = False
