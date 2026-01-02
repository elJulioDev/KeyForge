"""
Constantes y configuraciones globales del proyecto
"""
import sys
from pathlib import Path

def get_base_path():
    """Ruta de los archivos internos (Solo LECTURA: código, lang.json, imágenes)"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent

def get_config_path():
    """Ruta para guardar configuración (ESCRITURA: config.json)"""
    if getattr(sys, 'frozen', False):
        # Opción A: Verdaderamente Portable (guardar al lado del .exe)
        # Si llevas el .exe en un USB, la config viaja con él.
        config_dir = Path(sys.executable).parent / "data"
        
        # Opción B: Si prefieres usar AppData (menos portable, más limpio)
        # config_dir = Path.home() / 'AppData' / 'Local' / 'KeyForge'
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    else:
        return Path(__file__).parent.parent.parent / "data"

# --- Configuración de Rutas ---
BASE_DIR = get_base_path()      # Donde están los archivos del programa
CONFIG_DIR = get_config_path()  # Donde guardamos la configuración

# LANG_FILE se lee de los recursos internos (dentro del exe)
LANG_FILE = BASE_DIR / "data" / "lang.json" 

# CONFIG_FILE se guarda en la carpeta externa (fuera del exe)
CONFIG_FILE = CONFIG_DIR / "config.json"

# Crear carpeta de configuración si no existe
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# --- Configuración por Defecto ---
DEFAULT_CONFIG = {
    "rules": [],
    "enforce_app_focus": False,
    "target_app_name": "",
    "lang": "en",
    "theme": "darkly"
}