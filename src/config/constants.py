"""
Global constants and project configuration
"""
import sys
from pathlib import Path

# --- Version and Repository ---
CURRENT_VERSION = "1.5.0"
GITHUB_REPO_OWNER = "elJulioDev"
GITHUB_REPO_NAME = "KeyForge"

def get_base_path():
    """Path to internal files (READ-ONLY: code, lang.json, images)"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent

def get_config_path():
    """Path to save configuration (WRITE: config.json)"""
    if getattr(sys, 'frozen', False):
        # Option A: Truly Portable (save next to the .exe)
        # If you carry the .exe on a USB, the config travels with it.
        config_dir = Path(sys.executable).parent / "data"
        
        # Option B: If you prefer to use AppData (less portable, cleaner)
        # config_dir = Path.home() / 'AppData' / 'Local' / 'KeyForge'
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    else:
        return Path(__file__).parent.parent.parent / "data"

# --- Path Configuration ---
BASE_DIR = get_base_path()      # Where the program files are
CONFIG_DIR = get_config_path()  # Where we save the configuration

# LANG_FILE is read from internal resources (inside the exe)
LANG_FILE = BASE_DIR / "data" / "lang.json" 

# CONFIG_FILE is saved in the external folder (outside the exe)
CONFIG_FILE = CONFIG_DIR / "config.json"

# Create configuration folder if it does not exist
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# --- Default Configuration ---
DEFAULT_CONFIG = {
    "rules": [],
    "enforce_app_focus": False,
    "target_app_name": "",
    "lang": "en",
    "theme": "darkly"
}
