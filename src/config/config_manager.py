"""
Configuration and translations manager
"""
import json
import copy
import os
import tempfile
from .constants import CONFIG_FILE, LANG_FILE, DEFAULT_CONFIG
from .translation_manager import TranslationManager

try:
    from ..utils.logger import get_logger
    logger = get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# POSIX file locking (no-op fallback on Windows)
try:
    import fcntl
except ImportError:
    fcntl = None


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
                logger.info(f"Configuration loaded from: {CONFIG_FILE}")
                return config
            else:
                logger.info("No configuration file found, using default values")
                return copy.deepcopy(DEFAULT_CONFIG)
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return copy.deepcopy(DEFAULT_CONFIG)
    
    def save_config(self, config_data):
        """
        Saves the updated configuration preserving other keys (like 'lang').
        
        The write is atomic (temp file + os.replace) and guarded by a file
        lock so a crash mid-write or a second instance can never leave a
        truncated/corrupt config.json.
        
        Args:
            config_data (dict): Dictionary with the configuration to save
        """
        lock_fd = None
        try:
            if not isinstance(config_data, dict):
                raise TypeError(f"config_data must be a dict, got {type(config_data).__name__}")

            # Serialize first: json.dump can fail (e.g. non-serializable
            # value) and that must not truncate the existing file.
            # Atomic write: write to a temp file, then os.replace() so a
            # crash mid-write never leaves a truncated/corrupt config.
            with self._config_lock():
                current_config = self._read_current_config()
                current_config.update(config_data)

                serialized = json.dumps(current_config, indent=4, ensure_ascii=False)

                CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp_path = tempfile.mkstemp(
                    dir=str(CONFIG_FILE.parent),
                    prefix=CONFIG_FILE.name + ".",
                    suffix=".tmp"
                )
                try:
                    with os.fdopen(fd, 'w', encoding='utf-8') as f:
                        f.write(serialized)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp_path, CONFIG_FILE)
                except Exception:
                    # Clean up the temp file if the write or rename failed
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    raise

            logger.info(f"Configuration saved to: {CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False

    def _read_current_config(self):
        """Reads the current config, or the defaults the first time so a
        partial save never persists an incomplete file."""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error reading existing configuration: {e}")
        return copy.deepcopy(DEFAULT_CONFIG)

    @staticmethod
    def _config_lock():
        """Context manager that holds an exclusive advisory lock while the
        config file is read+written, so two instances can't clobber each
        other. The lock lives on a dedicated .lock file (not the config
        itself: os.replace swaps the config inode, which would void a lock
        held on the old file). No-op where fcntl is unavailable (Windows)."""
        import contextlib

        @contextlib.contextmanager
        def _locked():
            fd = None
            try:
                CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
                if fcntl is not None:
                    lock_path = CONFIG_FILE.parent / (CONFIG_FILE.name + ".lock")
                    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
                    fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                if fd is not None:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except Exception:
                        pass
                    os.close(fd)

        return _locked()
    
    def get_translation(self, key):
        """Gets a translation by key"""
        return self.tr_manager.tr(key)
