"""
Constantes y configuraciones globales del proyecto
"""
from pathlib import Path

# --- Configuración de Rutas ---
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LANG_FILE = DATA_DIR / "lang.json"
CONFIG_FILE = DATA_DIR / "config.json"

# Crear carpeta data si no existe
DATA_DIR.mkdir(exist_ok=True)

# --- Configuración por Defecto ---
DEFAULT_CONFIG = {
    "mode": "mantener",
    "key_to_replace": "alt",
    "replacement_key": "shift",
    "enforce_app_focus": True,
    "target_app_name": "",
    "lang": "en"
}
