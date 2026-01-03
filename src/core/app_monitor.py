"""
src/core/app_monitor.py
Monitor de aplicaciones activas - Versión Ultra-Filtrada
Elimina apps UWP suspendidas, procesos fantasma y ventanas de sistema.
"""

import sys
import os
import time
import ctypes
from typing import List, Optional, Callable

try:
    from ..utils.logger import get_logger
    logger = get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# --- CONSTANTES WIN32 ---
DWMWA_CLOAKED = 13
GWL_EXSTYLE = -20
GW_OWNER = 4
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

# Definiciones de tipos para ctypes
if sys.platform == 'win32':
    try:
        from ctypes import wintypes
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    except Exception:
        WNDENUMPROC = None


class AppMonitor:
    """
    Monitorea aplicaciones activas con filtrado agresivo de basura del sistema.
    """
    
    def __init__(self):
        self.target_app_name = ""
        self.enforce_app_focus = True
        self.target_app_is_active = False
        
        # Caché
        self._cache = {
            "hwnd": None,
            "title": "",
            "timestamp": 0
        }
        self._cache_timeout = 0.05
        
        # Inicializar APIs
        self._init_win32()
    
    def _init_win32(self):
        """Inicializa user32 y dwmapi"""
        if sys.platform == 'win32':
            try:
                self._user32 = ctypes.windll.user32
                self._dwmapi = ctypes.windll.dwmapi 
                self._win32_available = True
                logger.info("Win32 API + DWM inicializados correctamente")
            except Exception as e:
                self._user32 = None
                self._dwmapi = None
                self._win32_available = False
                logger.warning(f"Win32 API no disponible: {e}")
        else:
            self._user32 = None
            self._win32_available = False
    
    def set_target_app(self, app_name: str):
        self.target_app_name = app_name
    
    def set_enforce_focus(self, enforce: bool):
        self.enforce_app_focus = enforce
    
    def is_target_app_active(self) -> bool:
        if not self.enforce_app_focus:
            return True
        try:
            if self._win32_available:
                active_title = self._get_active_window_win32()
            else:
                active_title = self._get_active_window_fallback()
            
            if active_title and self.target_app_name.lower() in active_title.lower():
                return True
        except Exception:
            pass
        return False
    
    def _get_active_window_win32(self) -> str:
        current_time = time.time()
        if (current_time - self._cache["timestamp"]) < self._cache_timeout:
            return self._cache["title"]
        
        try:
            hwnd = self._user32.GetForegroundWindow()
            if hwnd == self._cache["hwnd"]:
                self._cache["timestamp"] = current_time
                return self._cache["title"]
            
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                title = ""
            else:
                buffer = ctypes.create_unicode_buffer(length + 1)
                self._user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value
            
            self._cache = {"hwnd": hwnd, "title": title, "timestamp": current_time}
            return title
        except Exception:
            return ""
    
    def _get_active_window_fallback(self) -> str:
        try:
            import pygetwindow as gw
            active_window = gw.getActiveWindow()
            if active_window: return active_window.title
        except Exception:
            pass
        return ""
    
    def update_status(self) -> bool:
        self.target_app_is_active = self.is_target_app_active()
        return self.target_app_is_active
    
    # -------------------------------------------------------------------------
    # ESCANEO DE VENTANAS
    # -------------------------------------------------------------------------
    def get_all_windows(self) -> List[str]:
        if self._win32_available:
            return self._get_windows_win32_list()
        else:
            return self._get_windows_fallback_list()

    def _get_windows_win32_list(self) -> List[str]:
        """
        Lista ventanas aplicando filtros estrictos para eliminar basura UWP y sistema.
        """
        titles = []
        my_pid = os.getpid()

        # LISTA NEGRA EXTENDIDA
        # Incluye procesos de sistema y UWP que suelen quedar en background
        garbage_titles = {
            "Program Manager", 
            "Default IME", 
            "MSCTFIME UI", 
            "NVIDIA GeForce Overlay",
            "Microsoft Text Input Application",
            "Windows Input Experience",
            "Settings", 
            "Configuración",
            "Calculator", 
            "Calculadora",
            "Cortana",
            "Search",
            "Start",
            "Inicio"
        }

        def enum_window_callback(hwnd, lParam):
            # 1. Filtro: ¿Es visible?
            if not self._user32.IsWindowVisible(hwnd):
                return True
            
            # 2. Filtro: Excluir KeyForge
            process_id = ctypes.c_ulong()
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if process_id.value == my_pid:
                return True

            # 3. Filtro DWM: Apps suspendidas (Cloaked)
            if self._dwmapi:
                is_cloaked = ctypes.c_int(0)
                hr = self._dwmapi.DwmGetWindowAttribute(
                    hwnd, 
                    DWMWA_CLOAKED, 
                    ctypes.byref(is_cloaked), 
                    ctypes.sizeof(is_cloaked)
                )
                if hr == 0 and is_cloaked.value != 0:
                    return True 

            # 4. Filtro Estilo: ToolWindows y Owners
            ex_style = self._user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            owner = self._user32.GetWindow(hwnd, GW_OWNER)
            
            if (ex_style & WS_EX_TOOLWINDOW) and not (ex_style & WS_EX_APPWINDOW):
                return True
            if owner != 0 and not (ex_style & WS_EX_APPWINDOW):
                return True

            # 5. NUEVO: Filtro de Dimensiones
            # Muchas apps "invisibles" tienen tamaño 0x0 o 1x1 aunque digan ser visibles
            rect = wintypes.RECT()
            self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w < 10 or h < 10:
                return True
            
            # 6. Obtener y verificar Título
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
                
            buff = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, buff, length + 1)
            text = buff.value
            
            if not text.strip():
                return True
                
            # Verificar contra lista negra
            if text in garbage_titles:
                return True
            
            titles.append(text)
            return True

        if WNDENUMPROC:
            self._user32.EnumWindows(WNDENUMPROC(enum_window_callback), 0)
        
        return sorted(list(set(titles)))

    def _get_windows_fallback_list(self) -> List[str]:
        try:
            import pygetwindow as gw
            all_windows = gw.getAllTitles()
            return sorted(list(set(w for w in all_windows if w.strip())))
        except Exception:
            return []

    def use_event_monitoring(self, callback: Callable[[bool], None]) -> bool:
        try:
            from .window_event_monitor import WindowEventMonitor, is_event_monitoring_available
            if not is_event_monitoring_available(): return False
            
            def on_window_change(window_title: str):
                self.target_app_is_active = self.target_app_name.lower() in window_title.lower()
                if callback: callback(self.target_app_is_active)
            
            self.event_monitor = WindowEventMonitor(on_window_change)
            self.event_monitor.start()
            return True
        except Exception:
            return False
    
    def stop_event_monitoring(self):
        if hasattr(self, 'event_monitor'):
            try:
                self.event_monitor.stop()
            except Exception:
                pass