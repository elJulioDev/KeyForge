"""
Constantes y configuraciones globales del proyecto
"""

import sys
from pathlib import Path

def get_base_path():
    """
    Obtiene la ruta base del proyecto, compatible con PyInstaller.
    
    Cuando el código se ejecuta normalmente, usa __file__.
    Cuando está empaquetado con PyInstaller, usa sys._MEIPASS.
    """
    if getattr(sys, 'frozen', False):
        # El código está siendo ejecutado como un ejecutable de PyInstaller
        # sys._MEIPASS apunta a la carpeta temporal donde PyInstaller extrae los archivos
        base_path = Path(sys._MEIPASS)
    else:
        # El código está siendo ejecutado como un script de Python normal
        base_path = Path(__file__).parent.parent.parent
    
    return base_path


def get_data_path():
    """
    Obtiene la ruta de la carpeta 'data', compatible con PyInstaller.
    
    En modo de desarrollo: usa la carpeta data del proyecto.
    En modo empaquetado: usa una carpeta en el directorio del usuario.
    """
    if getattr(sys, 'frozen', False):
        # Cuando está empaquetado, guardar data en una ubicación permanente
        # (no en _MEIPASS que es temporal)
        if sys.platform == 'win32':
            # Windows: usar AppData
            app_data = Path.home() / 'AppData' / 'Local' / 'KeyForge'
        else:
            # Linux/Mac: usar .config
            app_data = Path.home() / '.config' / 'KeyForge'
        
        app_data.mkdir(parents=True, exist_ok=True)
        return app_data
    else:
        # En desarrollo, usar la carpeta data del proyecto
        return BASE_DIR / "data"


# --- Configuración de Rutas ---
BASE_DIR = get_base_path()
DATA_DIR = get_data_path()
LANG_FILE = DATA_DIR / "lang.json"
CONFIG_FILE = DATA_DIR / "config.json"

# Crear carpeta data si no existe
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- Configuración por Defecto Actualizada ---
DEFAULT_CONFIG = {
    "rules": [],               # Lista limpia de reglas
    "enforce_app_focus": True,
    "target_app_name": "",
    "lang": "en"
}
