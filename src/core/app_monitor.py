"""
src/core/app_monitor.py
Active application monitor - Ultra-Filtered Version
Removes suspended UWP apps, ghost processes, and system windows.
"""

import sys
import os
import time
import json
import ast
import ctypes
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Callable

try:
    from ..utils.logger import get_logger
    logger = get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# --- WIN32 CONSTANTS ---
DWMWA_CLOAKED = 13
GWL_EXSTYLE = -20
GW_OWNER = 4
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

# Type definitions for ctypes
if sys.platform == 'win32':
    try:
        from ctypes import wintypes
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    except Exception:
        WNDENUMPROC = None


class AppMonitor:
    """
    Monitors active applications with aggressive system-garbage filtering.
    """
    
    def __init__(self):
        self.target_app_name = ""
        self.enforce_app_focus = True
        self.target_app_is_active = False
        
        # Cache
        self._cache = {
            "hwnd": None,
            "title": "",
            "timestamp": 0
        }
        self._cache_timeout = 0.05
        
        # Initialize APIs
        self._init_win32()
        self._detect_session()
    
    def _detect_session(self):
        """
        Detects the current desktop session and which backend can detect
        windows. Populates:
        - self.session: 'windows' | 'x11' | 'wayland'
        - self.wm: which compositor is running ('kwin', 'mutter', 'sway',
          'hyprland', 'generic', or None when undetectable)
        """
        if sys.platform == 'win32':
            self.session = 'windows'
            self.wm = 'windows'
            return

        self.session = 'wayland' if os.environ.get('WAYLAND_DISPLAY') else 'x11'

        desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
        session_desktop = os.environ.get('XDG_SESSION_DESKTOP', '').lower()
        combined = f"{desktop} {session_desktop}"

        if 'kde' in combined or 'plasma' in combined:
            self.wm = 'kwin'
        elif 'gnome' in combined or 'unity' in combined:
            self.wm = 'mutter'
        elif 'sway' in combined:
            self.wm = 'sway'
        elif 'hyprland' in combined:
            self.wm = 'hyprland'
        else:
            self.wm = 'generic'

    def supports_window_detection(self) -> bool:
        """
        True when the current session can detect windows (both the window
        list and the active window). On sessions where no backend applies,
        the focus feature is hidden in the UI.
        """
        if self.session == 'windows':
            return self._win32_available
        if self.session == 'x11':
            return bool(shutil.which('wmctrl') or shutil.which('xdotool'))
        # Wayland
        if self.wm == 'kwin':
            return bool(shutil.which('dbus-send'))
        if self.wm == 'mutter':
            return bool(shutil.which('gdbus'))
        if self.wm == 'sway':
            return bool(shutil.which('swaymsg'))
        if self.wm == 'hyprland':
            return bool(shutil.which('hyprctl'))
        return False
    
    def _init_win32(self):
        """Initialize user32 and dwmapi with proper ctypes signatures"""
        if sys.platform == 'win32':
            try:
                self._user32 = ctypes.windll.user32
                self._dwmapi = ctypes.windll.dwmapi

                # Set proper argtypes/restype to avoid 32-bit truncation of
                # HWND values on 64-bit Windows.
                self._user32.IsWindowVisible.argtypes = [wintypes.HWND]
                self._user32.IsWindowVisible.restype = wintypes.BOOL
                self._user32.GetWindowThreadProcessId.argtypes = [
                    wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
                self._user32.GetWindowRect.argtypes = [
                    wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
                self._user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
                self._user32.GetWindowTextW.argtypes = [
                    wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
                self._user32.GetForegroundWindow.restype = wintypes.HWND
                self._user32.GetWindow.argtypes = [wintypes.HWND, ctypes.c_uint]
                self._user32.GetWindow.restype = wintypes.HWND
                self._user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
                self._dwmapi.DwmGetWindowAttribute.argtypes = [
                    wintypes.HWND, wintypes.DWORD,
                    ctypes.c_void_p, wintypes.DWORD]
                self._dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long

                self._win32_available = True
                logger.info("Win32 API + DWM initialized successfully")
            except Exception as e:
                self._user32 = None
                self._dwmapi = None
                self._win32_available = False
                logger.warning(f"Win32 API unavailable: {e}")
        else:
            self._user32 = None
            self._win32_available = False

    def _get_window_long(self, hwnd, index):
        """Reads a window long value using the 64-bit-aware API on Windows"""
        if sys.platform == 'win32':
            try:
                func = getattr(self._user32, 'GetWindowLongPtrW', None)
                if func is None:
                    func = self._user32.GetWindowLongW
                func.argtypes = [wintypes.HWND, ctypes.c_int]
                func.restype = ctypes.c_ssize_t
                return func(hwnd, index)
            except Exception:
                try:
                    return self._user32.GetWindowLongW(hwnd, index)
                except Exception:
                    return 0
        return 0

    def _get_window_title(self, hwnd):
        """Gets the title of a window by handle (Win32)"""
        try:
            length = self._user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return ""
            buffer = ctypes.create_unicode_buffer(length + 1)
            self._user32.GetWindowTextW(hwnd, buffer, length + 1)
            return buffer.value
        except Exception:
            return ""
    
    def set_target_app(self, app_name: str):
        self.target_app_name = app_name
    
    def set_enforce_focus(self, enforce: bool):
        self.enforce_app_focus = enforce
    
    def is_target_app_active(self) -> bool:
        if not self.enforce_app_focus:
            return True
        if not self.supports_window_detection():
            return True
        try:
            active_title = self._get_active_window()
            
            if active_title and self.target_app_name.lower() in active_title.lower():
                return True
        except Exception:
            pass
        return False
    
    def _get_active_window(self) -> str:
        """Routes active-window detection to the backend for this session."""
        if self.session == 'windows':
            if not self._win32_available:
                return ""
            return self._get_active_window_win32()
        if self.session == 'x11':
            return self._get_active_window_fallback()
        if self.wm == 'kwin':
            return self._get_active_window_kwin()
        if self.wm == 'mutter':
            return self._get_active_window_gnome()
        if self.wm == 'sway':
            return self._get_active_window_sway()
        if self.wm == 'hyprland':
            return self._get_active_window_hyprland()
        return ""
    
    def _get_active_window_kwin(self) -> str:
        """
        Gets the title of the currently focused window on KDE Wayland.

        Uses a KWin scripting snippet whose print() lands in the user
        journal; the marker line is then read back with journalctl.
        Returns "" if KWin/D-Bus is unavailable.
        """
        current_time = time.time()
        if (current_time - self._cache["timestamp"]) < self._cache_timeout and self._cache["hwnd"] == "kwin":
            return self._cache["title"]

        title = self._run_kwin_script_active_window()

        self._cache = {"hwnd": "kwin", "title": title, "timestamp": current_time}
        return title

    def _run_kwin_script_active_window(self) -> str:
        """Loads and runs a KWin script that prints the active window caption."""
        cmd = shutil.which("qdbus6") or shutil.which("qdbus")
        if not cmd or not shutil.which("journalctl"):
            return ""

        script = 'var w = workspace.activeWindow;\nprint("KEYFORGE_ACTIVE:" + (w ? w.caption : "NONE"));\n'
        script_path = Path(tempfile.gettempdir()) / "kwin_active_window.js"
        try:
            if not script_path.exists() or script_path.read_text(encoding="utf-8") != script:
                script_path.write_text(script, encoding="utf-8")
        except Exception:
            return ""

        try:
            subprocess.run([cmd, "org.kde.KWin", "/Scripting",
                            "org.kde.kwin.Scripting.loadScript", str(script_path)],
                           capture_output=True, text=True, timeout=2.0)
            subprocess.run([cmd, "org.kde.KWin", "/Scripting",
                            "org.kde.kwin.Scripting.start"],
                           capture_output=True, text=True, timeout=2.0)
        except Exception:
            return ""

        try:
            result = subprocess.run(
                ["journalctl", "--user", "-o", "cat", "--since=5 seconds ago",
                 "--no-pager"],
                capture_output=True, text=True, timeout=2.0)
        except Exception:
            return ""

        # journalctl is chronological: take the LAST match, otherwise a rapid
        # Alt-Tab returns the title of the window focused ~5s ago.
        title = ""
        for line in result.stdout.splitlines():
            if line.startswith("KEYFORGE_ACTIVE:"):
                title = line.split(":", 1)[1].strip()

        # Unload the KWin script we just ran. Every 50ms poll would otherwise
        # stack script instances inside KWin until it runs out of memory.
        try:
            subprocess.run([cmd, "org.kde.KWin", "/Scripting",
                            "org.kde.kwin.Scripting.unloadScript",
                            str(script_path)],
                           capture_output=True, text=True, timeout=2.0)
        except Exception:
            pass
        return title

    def _get_active_window_gnome(self) -> str:
        """Gets the focused window title on GNOME (Wayland or X11)."""
        if not shutil.which("gdbus"):
            return ""
        out = self._run_cmd(
            ["gdbus", "call", "--session",
             "--dest", "org.gnome.Shell",
             "--object-path", "/org/gnome/Shell",
             "--method", "org.gnome.Shell.Eval",
             "global.display.focus_window?.get_title() || ''"])
        # gdbus returns a tuple like ('Title',) or ('',)
        try:
            result = ast.literal_eval(out)
            if isinstance(result, tuple) and result:
                return result[0] or ""
        except Exception:
            pass
        return ""

    def _get_active_window_sway(self) -> str:
        """Gets the focused window title on Sway via swaymsg tree."""
        if not shutil.which("swaymsg"):
            return ""
        out = self._run_cmd(["swaymsg", "-t", "get_tree"])
        if not out:
            return ""
        try:
            tree = json.loads(out)
        except Exception:
            return ""

        def find_focused(node):
            if node.get("focused") and node.get("name"):
                return node["name"]
            for child in node.get("nodes", []) + node.get("floating_nodes", []):
                title = find_focused(child)
                if title:
                    return title
            return ""

        return find_focused(tree)

    def _get_active_window_hyprland(self) -> str:
        """Gets the focused window title on Hyprland via hyprctl."""
        if not shutil.which("hyprctl"):
            return ""
        out = self._run_cmd(["hyprctl", "activewindow", "-j"])
        if not out:
            return ""
        try:
            data = json.loads(out)
            return data.get("title") or ""
        except Exception:
            return ""

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
        current_time = time.time()
        if (current_time - self._cache["timestamp"]) < self._cache_timeout and self._cache["hwnd"] == "fallback":
            return self._cache["title"]

        title = ""
        if shutil.which("xdotool"):
            title = self._run_cmd(["xdotool", "getactivewindow", "getwindowname"]).strip()

        if not title:
            try:
                import pygetwindow as gw
                active_window = gw.getActiveWindow()
                if active_window:
                    title = active_window.title
            except Exception:
                pass

        self._cache = {"hwnd": "fallback", "title": title, "timestamp": current_time}
        return title

    @staticmethod
    def _run_cmd(args) -> str:
        """Run an external command (wmctrl/xdotool) with a short timeout and without crashing if it fails"""
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=2.0)
            return result.stdout
        except Exception:
            return ""
    
    def update_status(self) -> bool:
        self.target_app_is_active = self.is_target_app_active()
        return self.target_app_is_active
    
    # -------------------------------------------------------------------------
    # WINDOW SCANNING
    # -------------------------------------------------------------------------
    def get_all_windows(self) -> List[str]:
        if self.session == 'windows':
            if not self._win32_available:
                return []
            return self._get_windows_win32_list()
        if self.session == 'x11':
            return self._get_windows_fallback_list()
        if self.wm == 'kwin':
            return self._get_windows_kwin_list()
        if self.wm == 'mutter':
            return self._get_windows_gnome_list()
        if self.wm == 'sway':
            return self._get_windows_sway_list()
        if self.wm == 'hyprland':
            return self._get_windows_hyprland_list()
        return []

    def _get_windows_win32_list(self) -> List[str]:
        """
        Lists windows applying strict filters to remove UWP and system garbage.

        If the strict filters drop every window (e.g. a DWM/theme edge case on
        a given Windows build), falls back to a lenient pass so the app list
        is never empty while real windows exist.
        """
        titles = []
        my_pid = os.getpid()

        # BLACKLIST: Only block system processes that we NEVER want to target.
        # I've removed apps like 'Calculator', 'Settings', etc. from this hard list
        # because your filters #3 (Cloaked) and #5 (Dimensions) should already remove
        # their ghost/background versions.
        garbage_titles = {
            "Program Manager", 
            "Default IME", 
            "MSCTFIME UI", 
            "NVIDIA GeForce Overlay",
            "Microsoft Text Input Application",
            "Windows Input Experience",
            "Cortana",
            "Search",
            "Start",
            "Inicio",
            "logs",
            "Configuración",
            "Settings"
            # The following have been removed to allow their detection if they are real windows:
            # "Settings", "Configuración", "Calculator", "Calculadora",
            # "Movies & TV", "Películas y TV"
        }

        def enum_window_callback(hwnd, lParam):
            # 1. Filter: Is it visible?
            if not self._user32.IsWindowVisible(hwnd):
                return True
            
            # 2. Filter: Exclude KeyForge
            process_id = wintypes.DWORD()
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if process_id.value == my_pid:
                return True

            # 3. DWM Filter: Suspended apps (Cloaked)
            # THIS IS KEY FOR UWP APPS: Removes Calculator/Settings when minimized/suspended
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

            # 4. Style Filter: ToolWindows and Owners
            ex_style = self._get_window_long(hwnd, GWL_EXSTYLE)
            owner = self._user32.GetWindow(hwnd, GW_OWNER)
            
            if (ex_style & WS_EX_TOOLWINDOW) and not (ex_style & WS_EX_APPWINDOW):
                return True
            if owner != 0 and not (ex_style & WS_EX_APPWINDOW):
                return True

            # 5. Dimensions Filter
            # Removes ghost windows of 0x0 or 1x1
            rect = wintypes.RECT()
            self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w < 10 or h < 10:
                return True
            
            # 6. Get and verify Title
            text = self._get_window_title(hwnd)
            if not text or not text.strip():
                return True
                
            # Check against blacklist
            if text in garbage_titles:
                # SMART EXCEPTION:
                # If for any reason a "garbage" window (e.g. Cortana or Start)
                # is the ACTIVE window (has user focus), we allow it through.
                # This fulfills the "if they are being used" requirement.
                active_hwnd = self._user32.GetForegroundWindow()
                if hwnd != active_hwnd:
                    return True
                # If it is the active window, let it pass even if blacklisted
            
            titles.append(text)
            return True

        if WNDENUMPROC:
            self._user32.EnumWindows(WNDENUMPROC(enum_window_callback), 0)
        
        if titles:
            return sorted(list(set(titles)))

        # STRICT FILTERS RETURNED NOTHING: retry with a lenient pass so the
        # dropdown is never empty while there are real, titled, visible windows.
        logger.warning("Strict window filters returned no titles; using lenient fallback")
        return self._get_windows_lenient_list(my_pid)

    def _get_windows_lenient_list(self, my_pid) -> List[str]:
        """Minimal filter: visible windows with a non-empty title, excluding KeyForge."""
        titles = []

        def enum_window_callback(hwnd, lParam):
            if not self._user32.IsWindowVisible(hwnd):
                return True
            process_id = wintypes.DWORD()
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if process_id.value == my_pid:
                return True
            text = self._get_window_title(hwnd)
            if text and text.strip():
                titles.append(text)
            return True

        if WNDENUMPROC:
            self._user32.EnumWindows(WNDENUMPROC(enum_window_callback), 0)
        return sorted(list(set(titles)))

    def _get_windows_fallback_list(self) -> List[str]:
        """
        Lists windows on non-Windows platforms.

        Combines results from every tool that works on the current session:
        - Wayland (KDE): KWin windows runner via D-Bus
        - X11: wmctrl + xdotool
        - fallback: pygetwindow

        Results are unioned and deduplicated instead of stopping at the first
        tool that returns something, because a tool may miss windows the
        others find. KeyForge's own window is skipped so the target dropdown
        never contains the app itself.
        """
        titles = []

        # Method 1 (Wayland/KDE): KWin windows runner over D-Bus. Native
        # Wayland windows are invisible to wmctrl/xdotool (X11 only), so on
        # Wayland this is the only reliable source.
        if self._is_wayland_session():
            titles += self._get_windows_kwin_list()

        # Method 2: wmctrl -l (X11)
        if shutil.which("wmctrl"):
            out = self._run_cmd(["wmctrl", "-l"])
            for line in out.splitlines():
                # Format: <id> <desktop> <host> <title...>
                parts = line.split(None, 3)
                if len(parts) == 4 and parts[3].strip():
                    titles.append(parts[3].strip())

        # Method 3: xdotool (finds windows wmctrl may miss)
        if shutil.which("xdotool"):
            # "." matches name, class, classname and role of visible windows;
            # then fetch each title individually (getwindowname is reliable).
            out = self._run_cmd(["xdotool", "search", "--onlyvisible", "."])
            for win_id in out.split():
                name = self._run_cmd(["xdotool", "getwindowname", win_id]).strip()
                if name:
                    titles.append(name)

        # Method 4: pygetwindow (last resort)
        try:
            import pygetwindow as gw
            titles += [w for w in gw.getAllTitles() if w.strip()]
        except Exception:
            pass

        # Exclude KeyForge's own window and deduplicate
        return sorted(set(
            t for t in titles
            if t.strip() and not t.lower().startswith("keyforge")
        ))

    @staticmethod
    def _is_wayland_session() -> bool:
        """True if the session runs under Wayland."""
        return os.environ.get("WAYLAND_DISPLAY") is not None

    def _get_windows_kwin_list(self) -> List[str]:
        """
        Lists windows on KDE Plasma via the KWin windows runner (D-Bus).

        Works for native Wayland windows that wmctrl/xdotool cannot see.
        Returns empty list if KWin/D-Bus is unavailable.
        """
        cmd = shutil.which("dbus-send")
        if not cmd:
            return []
        try:
            result = subprocess.run(
                [cmd, "--session", "--print-reply=literal",
                 "--dest=org.kde.KWin", "/WindowsRunner",
                 "org.kde.krunner1.Match", "string:"],
                capture_output=True, text=True, timeout=2.0)
        except Exception:
            return []
        if result.returncode != 0:
            return []

        # Each window is a struct:  0_<uuid>   <title>   int32 <relevance>
        # The title is the text between the uuid and the 'int32' field.
        import re
        titles = []
        for m in re.finditer(r"0_\{[^}]+\}\s+(.*?)\s{2,}int32\s+\d+", result.stdout):
            title = m.group(1).strip()
            if not title:
                continue
            # KRunner appends the .desktop id (e.g. "org.kde.dolphin",
            # "utilities-terminal") after several spaces; strip it.
            title = re.sub(r"\s{2,}\S.*$", "", title).strip()
            if title:
                titles.append(title)
        return list(dict.fromkeys(titles))

    def _get_windows_gnome_list(self) -> List[str]:
        """Lists window titles on GNOME via the Shell's window introspection."""
        if not shutil.which("gdbus"):
            return []
        out = self._run_cmd(
            ["gdbus", "call", "--session",
             "--dest", "org.gnome.Shell",
             "--object-path", "/org/gnome/Shell",
             "--method", "org.gnome.Shell.Eval",
             "JSON.stringify(global.get_window_actors().map(a => a.meta_window.get_title()))"])
        # gdbus returns a tuple like ('["A", "B"]',)
        try:
            result = ast.literal_eval(out)
            if isinstance(result, tuple) and result:
                titles = json.loads(result[0])
                return sorted(set(t for t in titles if t and not t.lower().startswith("keyforge")))
        except Exception:
            pass
        return []

    def _get_windows_sway_list(self) -> List[str]:
        """Lists window titles on Sway from the swaymsg tree."""
        if not shutil.which("swaymsg"):
            return []
        out = self._run_cmd(["swaymsg", "-t", "get_tree"])
        if not out:
            return []
        try:
            tree = json.loads(out)
        except Exception:
            return []

        titles = []
        def walk(node):
            if node.get("name") and (node.get("app_id") or node.get("window_properties")):
                titles.append(node["name"])
            for child in node.get("nodes", []) + node.get("floating_nodes", []):
                walk(child)
        walk(tree)
        return sorted(set(t for t in titles if not t.lower().startswith("keyforge")))

    def _get_windows_hyprland_list(self) -> List[str]:
        """Lists window titles on Hyprland via hyprctl clients."""
        if not shutil.which("hyprctl"):
            return []
        out = self._run_cmd(["hyprctl", "clients", "-j"])
        if not out:
            return []
        try:
            clients = json.loads(out)
        except Exception:
            return []
        return sorted(set(
            c.get("title") for c in clients
            if c.get("title") and not c["title"].lower().startswith("keyforge")
        ))

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