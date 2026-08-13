"""
Gestor de traducciones con soporte para hot-reload
"""
import json
from pathlib import Path


class TranslationManager:
    """
    Gestiona traducciones con soporte para hot-reload.
    
    Estructura esperada de lang.json:
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
            lang_file_path: Path al archivo lang.json
        """
        self.lang_file = Path(lang_file_path)
        self._translations = {}  # {lang_code: {key: value}}
        self._meta = {}          # {lang_code: {name, native}}
        self.current_lang = "en"
        self._subscribers = []   # Componentes suscritos a cambios
        self._is_updating = False  # Guard contra re-entrancy
        
    def load(self):
        """Carga lang.json con estructura mejorada"""
        try:
            if not self.lang_file.exists():
                print(f"Archivo de traducciones no encontrado: {self.lang_file}")
                return False
                
            with open(self.lang_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Soporte para estructura nueva (meta + translations)
            if "translations" in data:
                self._translations = data["translations"]
                self._meta = data.get("meta", {})
            else:
                # Fallback: estructura vieja (solo traducciones)
                self._translations = data
                self._meta = {}
            
            print(f"Traducciones cargadas: {list(self._translations.keys())}")
            return True
            
        except Exception as e:
            print(f"Error al cargar traducciones: {e}")
            self._translations = {"es": {}, "en": {}}
            return False
    
    def tr(self, key, **kwargs):
        """
        Traduce una clave con fallback chain: actual → inglés → key
        
        Args:
            key: Clave de traducción
            **kwargs: Parámetros para format() (ej: app="MiApp")
            
        Returns:
            str: Texto traducido o key si no existe
        """
        # 1. Buscar en idioma actual
        text = self._translations.get(self.current_lang, {}).get(key)
        
        # 2. Fallback a inglés
        if text is None:
            text = self._translations.get("en", {}).get(key)
        
        # 3. Fallback a la key misma
        if text is None:
            text = key
        
        # 4. Aplicar format si hay kwargs
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass  # Si falta algún parámetro, retornar sin formato
        
        return text
    
    def __call__(self, key, **kwargs):
        """Permite llamar directamente: tr("key", app="X")"""
        return self.tr(key, **kwargs)
    
    def get_available_languages(self):
        """
        Retorna diccionario de idiomas disponibles desde meta.
        
        Returns:
            dict: {code: {name, native}} o dict vacío si no hay meta
        """
        if self._meta:
            return self._meta.copy()
        
        # Fallback: generar desde traducciones disponibles
        return {lang: {"name": lang.upper(), "native": lang.upper()} 
                for lang in self._translations.keys()}
    
    def get_language_name(self, lang_code, display_lang=None):
        """
        Retorna nombre del idioma para UI.
        
        Args:
            lang_code: Código del idioma (ej: "es")
            display_lang: Idioma en que mostrar el nombre (default: idioma actual)
            
        Returns:
            str: Nombre del idioma
        """
        if display_lang is None:
            display_lang = self.current_lang
        
        # Buscar en meta
        if lang_code in self._meta:
            lang_info = self._meta[lang_code]
            return lang_info.get(display_lang, lang_info.get("native", lang_code))
        
        return lang_code.upper()
    
    def set_language(self, lang_code):
        """
        Cambia idioma y notifica a suscriptores.
        
        Args:
            lang_code: Nuevo código de idioma
            
        Returns:
            bool: True si el idioma cambió, False si era el mismo
        """
        if lang_code == self.current_lang:
            return False
            
        if lang_code not in self._translations:
            print(f"Idioma no disponible: {lang_code}")
            return False
        
        old_lang = self.current_lang
        self.current_lang = lang_code
        
        print(f"Idioma cambiado: {old_lang} → {lang_code}")
        self._notify_subscribers()
        return True
    
    def subscribe(self, component):
        """
        Registra componente para notificaciones de cambio de idioma.
        
        Args:
            component: Instancia con método update_translations()
        """
        if component not in self._subscribers:
            self._subscribers.append(component)
    
    def unsubscribe(self, component):
        """
        Elimina componente de suscriptores.
        
        Args:
            component: Instancia a eliminar
        """
        try:
            self._subscribers.remove(component)
        except ValueError:
            pass
    
    def _notify_subscribers(self):
        """Llama update_translations() en todos los suscriptores"""
        if self._is_updating:
            return  # Prevenir re-entrancy
        
        self._is_updating = True
        try:
            for component in self._subscribers[:]:  # Copia para evitar modificación
                try:
                    component.update_translations()
                except Exception as e:
                    print(f"Error actualizando componente: {e}")
        finally:
            self._is_updating = False
