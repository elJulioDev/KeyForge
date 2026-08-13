"""
Gestor de configuración y traducciones
"""
import json
from pathlib import Path
from .constants import CONFIG_FILE, LANG_FILE, DEFAULT_CONFIG
from .translation_manager import TranslationManager


class ConfigManager:
    """Maneja la carga, guardado y aplicación de configuraciones"""
    
    def __init__(self):
        self.config = self.load_config()
        
        # Inicializar TranslationManager
        self.tr_manager = TranslationManager(LANG_FILE)
        self.tr_manager.load()
        self.tr_manager.current_lang = self.config.get("lang", "en")
        
        # Alias para backward compatibility temporal
        # NOTA: Esto se eliminará cuando todos los componentes usen tr_manager.tr()
        self.tr = self.tr_manager
    
    def load_config(self):
        """
        Carga la configuración desde el archivo JSON.
        Si no existe, retorna la configuración por defecto.
        """
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"Configuración cargada desde: {CONFIG_FILE}")
                return config
            else:
                print("No se encontró archivo de configuración, usando valores por defecto")
                return DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error al cargar configuración: {e}")
            return DEFAULT_CONFIG.copy()
    
    def save_config(self, config_data):
        """
        Guarda la configuración actualizada preservando otras claves (como 'lang').
        
        Args:
            config_data (dict): Diccionario con la configuración a guardar
        """
        try:
            # Leer la config actual
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    current_config = json.load(f)
            else:
                current_config = {}
            
            # Actualizar con los nuevos datos
            current_config.update(config_data)
            
            # Guardar
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, indent=4, ensure_ascii=False)
            
            print(f"Configuración guardada en: {CONFIG_FILE}")
            return True
        except Exception as e:
            print(f"Error al guardar configuración: {e}")
            return False
    
    def get_translation(self, key):
        """Obtiene una traducción por clave"""
        return self.tr_manager.tr(key)
