"""
Configuration and translations manager
"""
import json
from pathlib import Path
from .constants import CONFIG_FILE, LANG_FILE, DEFAULT_CONFIG
from .translation_manager import TranslationManager


class ConfigManager:
    """Handles loading, saving and applying configurations"""
    
    def __init__(self):
        self.config = self.load_config()
        
        # Initialize TranslationManager
        self.tr_manager = TranslationManager(LANG_FILE)
        self.tr_manager.load()
        self.tr_manager.current_lang = self.config.get("lang", "en")
        
        # Alias for temporary backward compatibility
        # NOTE: This will be removed when all components use tr_manager.tr()
        self.tr = self.tr_manager
    
    def load_config(self):
        """
        Loads the configuration from the JSON file.
        If it does not exist, returns the default configuration.
        """
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"Configuration loaded from: {CONFIG_FILE}")
                return config
            else:
                print("No configuration file found, using default values")
                return DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return DEFAULT_CONFIG.copy()
    
    def save_config(self, config_data):
        """
        Saves the updated configuration preserving other keys (like 'lang').
        
        Args:
            config_data (dict): Dictionary with the configuration to save
        """
        try:
            # Read the current config
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    current_config = json.load(f)
            else:
                current_config = {}
            
            # Update with the new data
            current_config.update(config_data)
            
            # Save
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, indent=4, ensure_ascii=False)
            
            print(f"Configuration saved to: {CONFIG_FILE}")
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def get_translation(self, key):
        """Gets a translation by key"""
        return self.tr_manager.tr(key)
