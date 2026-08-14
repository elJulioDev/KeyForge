"""
Professional logging system for KeyForge
Rotating logs with error analysis
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


class KeyForgeLogger:
    """
    Singleton logging system with automatic rotation.

    Features:
    - Rotating log files (5MB max)
    - Keeps the last 3 files
    - Professional format with timestamp and level
    - Logs to file + console (only critical errors)
    """
    
    _instance: Optional['KeyForgeLogger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._setup_logger()
    
    def _setup_logger(self):
        """Configure the logging system."""
        self.logger = logging.getLogger('KeyForge')
        self.logger.setLevel(logging.DEBUG)
        
        # Avoid duplicate handlers
        if self.logger.handlers:
            return
        
        # Professional format with colors for the console
        log_format = '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s | %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        formatter = logging.Formatter(log_format, datefmt=date_format)
        
        # --- HANDLER 1: Rotating file ---
        log_dir = self._get_log_directory()
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f'keyforge_{datetime.now().strftime("%Y%m%d")}.log'
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB per file
            backupCount=3,              # Keep the last 3 files
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # --- HANDLER 2: Console (only critical errors) ---
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self._get_colored_formatter())
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Remove logs older than the retention window on every start
        self.cleanup_old_logs()
        
        # Startup log
        self.logger.info("=" * 70)
        self.logger.info("KeyForge - Logging system initialized")
        self.logger.info(f"Log file: {log_file}")
        self.logger.info("=" * 70)
    
    def _get_log_directory(self) -> Path:
        """Determine the path of the log directory."""
        if sys.platform == 'win32':
            # Windows: AppData/Local/KeyForge/logs
            log_dir = Path.home() / 'AppData' / 'Local' / 'KeyForge' / 'logs'
        elif sys.platform == 'darwin':
            # macOS: ~/Library/Logs/KeyForge
            log_dir = Path.home() / 'Library' / 'Logs' / 'KeyForge'
        else:
            # Linux: ~/.local/share/keyforge/logs
            log_dir = Path.home() / '.local' / 'share' / 'keyforge' / 'logs'
        
        return log_dir
    
    def _get_colored_formatter(self) -> logging.Formatter:
        """
        Create a formatter with colors for the console.
        Only works on compatible terminals.
        """
        # ANSI codes for colors
        COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'
        }
        
        class ColoredFormatter(logging.Formatter):
            def format(self, record):
                levelname = record.levelname
                if levelname in COLORS:
                    record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
                try:
                    return super().format(record)
                finally:
                    # Restore the clean levelname: the record is shared with
                    # the file handler and must not keep ANSI codes.
                    record.levelname = levelname
        
        return ColoredFormatter(
            '%(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def get_logger(self) -> logging.Logger:
        """Return the logger instance."""
        return self.logger
    
    def cleanup_old_logs(self, days: int = 7):
        """
        Delete logs older than X days.
        
        Args:
            days: Number of days to keep
        """
        log_dir = self._get_log_directory()
        
        if not log_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (days * 86400)
        deleted_count = 0
        
        for log_file in log_dir.glob('*.log*'):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"Could not delete {log_file}: {e}")
        
        if deleted_count > 0:
            self.logger.info(f"Log cleanup: {deleted_count} files deleted")


class PerformanceLogger:
    """
    Logger specialized for performance metrics.
    
    Usage:
        with PerformanceLogger("Expensive operation"):
            # code to measure
    """
    
    def __init__(self, operation_name: str, threshold_ms: float = 10.0):
        """
        Args:
            operation_name: Name of the operation
            threshold_ms: Only log if it exceeds this time (ms)
        """
        self.operation_name = operation_name
        self.threshold_ms = threshold_ms
        self.logger = get_logger()
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        elapsed_ms = (time.perf_counter() - self.start_time) * 1000
        
        if elapsed_ms > self.threshold_ms:
            self.logger.warning(
                f"Slow operation: {self.operation_name} took {elapsed_ms:.2f}ms"
            )
        else:
            self.logger.debug(
                f"OK {self.operation_name}: {elapsed_ms:.3f}ms"
            )


# Convenience functions for quick access
def get_logger() -> logging.Logger:
    """Get the main logger instance."""
    return KeyForgeLogger().get_logger()


def log_exception(exception: Exception, context: str = ""):
    """
    Log an exception with full context.
    
    Args:
        exception: The exception to log
        context: Additional context about where it occurred
    """
    logger = get_logger()
    
    if context:
        logger.error(f"Exception in {context}: {exception}", exc_info=True)
    else:
        logger.error(f"Exception: {exception}", exc_info=True)


def log_startup_info():
    """Log system information at startup."""
    import platform
    logger = get_logger()
    
    logger.info("System Information:")
    logger.info(f"  OS: {platform.system()} {platform.release()}")
    logger.info(f"  Python: {platform.python_version()}")
    logger.info(f"  Architecture: {platform.machine()}")
    logger.info(f"  Processor: {platform.processor()}")