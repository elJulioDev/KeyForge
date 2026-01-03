"""
Sistema de logging profesional para KeyForge
Logs rotatorios con análisis de errores
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


class KeyForgeLogger:
    """
    Sistema de logging singleton con rotación automática.
    
    Características:
    - Archivos de log con rotación (5MB max)
    - Mantiene los últimos 3 archivos
    - Formato profesional con timestamp y nivel
    - Logs en archivo + consola (solo errores críticos)
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
        """Configura el sistema de logging"""
        self.logger = logging.getLogger('KeyForge')
        self.logger.setLevel(logging.DEBUG)
        
        # Evitar duplicación de handlers
        if self.logger.handlers:
            return
        
        # Formato profesional con colores para consola
        log_format = '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s | %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        formatter = logging.Formatter(log_format, datefmt=date_format)
        
        # --- HANDLER 1: Archivo con rotación ---
        log_dir = self._get_log_directory()
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f'keyforge_{datetime.now().strftime("%Y%m%d")}.log'
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB por archivo
            backupCount=3,              # Mantener últimos 3 archivos
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # --- HANDLER 2: Consola (solo errores críticos) ---
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self._get_colored_formatter())
        console_handler.setLevel(logging.WARNING)  # Solo warnings y errores
        
        # Agregar handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Log de inicio
        self.logger.info("=" * 70)
        self.logger.info("KeyForge - Sistema de logging inicializado")
        self.logger.info(f"Archivo de log: {log_file}")
        self.logger.info("=" * 70)
    
    def _get_log_directory(self) -> Path:
        """Determina la ruta del directorio de logs"""
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
        Crea un formatter con colores para la consola.
        Solo funciona en terminales compatibles.
        """
        # Códigos ANSI para colores
        COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Verde
            'WARNING': '\033[33m',  # Amarillo
            'ERROR': '\033[31m',    # Rojo
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'
        }
        
        class ColoredFormatter(logging.Formatter):
            def format(self, record):
                levelname = record.levelname
                if levelname in COLORS:
                    record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
                return super().format(record)
        
        return ColoredFormatter(
            '%(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def get_logger(self) -> logging.Logger:
        """Retorna la instancia del logger"""
        return self.logger
    
    def cleanup_old_logs(self, days: int = 7):
        """
        Elimina logs más antiguos que X días.
        
        Args:
            days: Cantidad de días a mantener
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
                    self.logger.warning(f"No se pudo eliminar {log_file}: {e}")
        
        if deleted_count > 0:
            self.logger.info(f"Limpieza de logs: {deleted_count} archivos eliminados")


class PerformanceLogger:
    """
    Logger especializado para métricas de rendimiento.
    
    Uso:
        with PerformanceLogger("Operación costosa"):
            # código a medir
    """
    
    def __init__(self, operation_name: str, threshold_ms: float = 10.0):
        """
        Args:
            operation_name: Nombre de la operación
            threshold_ms: Solo logear si excede este tiempo (ms)
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
                f"⚠️ Operación lenta: {self.operation_name} tomó {elapsed_ms:.2f}ms"
            )
        else:
            self.logger.debug(
                f"✓ {self.operation_name}: {elapsed_ms:.3f}ms"
            )


# Funciones de conveniencia para acceso rápido
def get_logger() -> logging.Logger:
    """Obtiene la instancia del logger principal"""
    return KeyForgeLogger().get_logger()


def log_exception(exception: Exception, context: str = ""):
    """
    Registra una excepción con contexto completo.
    
    Args:
        exception: La excepción a registrar
        context: Contexto adicional sobre dónde ocurrió
    """
    logger = get_logger()
    
    if context:
        logger.error(f"Excepción en {context}: {exception}", exc_info=True)
    else:
        logger.error(f"Excepción: {exception}", exc_info=True)


def log_startup_info():
    """Registra información del sistema al inicio"""
    import platform
    logger = get_logger()
    
    logger.info("Información del Sistema:")
    logger.info(f"  OS: {platform.system()} {platform.release()}")
    logger.info(f"  Python: {platform.python_version()}")
    logger.info(f"  Arquitectura: {platform.machine()}")
    logger.info(f"  Procesador: {platform.processor()}")