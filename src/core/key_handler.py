"""
Keyboard event handler with O(1) lookup
Optimized for minimal latency
"""

import keyboard
import time
import sys
import os
from typing import Dict, List, Optional, Tuple

# Professional logger (imported from the utils module)
try:
    from ..utils.logger import get_logger
    logger = get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def _patch_keyboard_linux_root_check():
    """
    keyboard._nixcommon.ensure_root() requires os.geteuid() == 0 without looking
    at the real permissions of /dev/uinput. With the udev rule + 'input' group
    (see README), real access already exists even if we're not root — the
    library's check is unnecessarily strict for that case.
    We replace it with one that validates real access to the device.
    """
    if not sys.platform.startswith('linux'):
        return
    try:
        import keyboard._nixcommon as _nixcommon
        import keyboard._nixkeyboard as _nixkeyboard

        def _ensure_device_access():
            if os.geteuid() == 0:
                return
            if os.access('/dev/uinput', os.W_OK):
                return
            raise ImportError(
                "No access to /dev/uinput. The 'input' group or the udev rule "
                "is missing (see README, 'Linux permissions' section), or you "
                "need to log out after adding yourself to the group."
            )

        # _nixkeyboard did "from ._nixcommon import ensure_root" on import,
        # leaving its own name in its namespace. Patching only _nixcommon won't
        # affect it; both must be patched.
        _nixcommon.ensure_root = _ensure_device_access
        _nixkeyboard.ensure_root = _ensure_device_access
    except Exception as e:
        logger.warning(f"Could not patch the 'keyboard' root check: {e}")


_patch_keyboard_linux_root_check()


def _patch_keyboard_dumpkeys_cache():
    """
    'dumpkeys' needs a real console descriptor (VT), something that doesn't
    exist inside a graphical terminal (Konsole/Wayland/X11). There it fails
    with "Couldn't get a file descriptor referring to the console", even with
    permissions over /dev/input and /dev/uinput — it's a kernel restriction
    (CAP_SYS_TTY_CONFIG), not fixable with udev.

    Solution: cache the 'dumpkeys' output once (generated with sudo, or from a
    real TTY with Ctrl+Alt+F3) and serve it from disk on every normal start,
    without invoking the binary again.
    """
    if not sys.platform.startswith('linux'):
        return
    try:
        from ..config.constants import CONFIG_DIR
        import keyboard._nixkeyboard as _nixkeyboard

        cache_dir = CONFIG_DIR / "dumpkeys_cache"
        cache_files = {
            ('dumpkeys', '--keys-only'): cache_dir / "keys_only.txt",
            ('dumpkeys', '--long-info'): cache_dir / "long_info.txt",
        }
        original_check_output = _nixkeyboard.check_output

        def _cached_check_output(cmd, *args, **kwargs):
            path = cache_files.get(tuple(cmd))
            if path is not None:
                if path.exists():
                    return path.read_text(encoding='utf-8')
                # First try: run the real binary (root or real TTY)
                # and, if it works, save the result for next time.
                output = original_check_output(cmd, *args, **kwargs)
                cache_dir.mkdir(parents=True, exist_ok=True)
                path.write_text(output, encoding='utf-8')
                return output
            return original_check_output(cmd, *args, **kwargs)

        _nixkeyboard.check_output = _cached_check_output
    except Exception as e:
        logger.warning(f"Could not enable the 'dumpkeys' cache: {e}")


_patch_keyboard_dumpkeys_cache()


def _patch_keyboard_linux_real_suppress():
    """
    The 'keyboard' library documents (its own README): "Key
    suppression/blocking only available on Windows". On Linux
    _nixkeyboard.listen() reads /dev/input/eventN passively and discards the
    callback's return value -> the original key ALWAYS reaches the system,
    regardless of whether there's a rule replacing it. Result: "A"->"S" types
    "AS", not "S".

    Real fix (what the driver does on Windows, we do it by hand here):
      1. EVIOCGRAB on each physical keyboard device: it stops delivering
         events to anyone else (Wayland/X11 included).
      2. We re-inject through the virtual device (uinput) every key that the
         callback does NOT block, so the rest of the keyboard is not lost.

    Along the way, it avoids the `exit()` that the library calls inside the
    reader thread when a device returns "Permission denied" (e.g. some ACPI
    power-button event without access): now that device is simply ignored
    instead of printing the warning and killing its thread.
    """
    if not sys.platform.startswith('linux'):
        return
    try:
        import fcntl
        import keyboard._nixcommon as _nixcommon
        import keyboard._nixkeyboard as _nixkeyboard

        EVIOCGRAB = 0x40044590

        def _safe_grabbed_input_file(self):
            if self._input_file is None:
                try:
                    self._input_file = open(self.path, 'rb')
                except IOError as e:
                    if e.strerror == 'Permission denied':
                        logger.warning(f"No access to {self.path}, that device is ignored.")
                    else:
                        logger.warning(f"Could not open {self.path}: {e}")
                    return None

                if self.path != 'uinput Fake Device':
                    try:
                        fcntl.ioctl(self._input_file, EVIOCGRAB, 1)
                    except OSError as e:
                        logger.warning(f"Could not grab {self.path} (EVIOCGRAB): {e}")

                import atexit as _atexit
                def try_close():
                    try:
                        self._input_file.close()
                    except Exception:
                        pass
                _atexit.register(try_close)
            return self._input_file

        _nixcommon.EventDevice.input_file = property(_safe_grabbed_input_file)

        import struct as _struct
        import threading as _threading

        def _safe_read_event(self):
            f = self.input_file
            if f is None:
                # Device without access: this thread cannot read anything,
                # it stays idle instead of blowing up with AttributeError.
                _threading.Event().wait()
            data = f.read(_struct.calcsize(_nixcommon.event_bin_format))
            seconds, microseconds, type_, code, value = _struct.unpack(_nixcommon.event_bin_format, data)
            return seconds + microseconds / 1e6, type_, code, value, self.path

        _nixcommon.EventDevice.read_event = _safe_read_event

        def _passthrough_listen(callback):
            _nixkeyboard.build_device()
            _nixkeyboard.build_tables()
            device = _nixkeyboard.device

            while True:
                time_, type_, code, value, device_id = device.read_event()
                if type_ != _nixcommon.EV_KEY:
                    continue

                scan_code = code
                event_type = _nixkeyboard.KEY_DOWN if value else _nixkeyboard.KEY_UP

                pressed_modifiers_tuple = tuple(sorted(_nixkeyboard.pressed_modifiers))
                names = (_nixkeyboard.to_name[(scan_code, pressed_modifiers_tuple)]
                         or _nixkeyboard.to_name[(scan_code, ())] or ['unknown'])
                name = names[0]

                if name in _nixkeyboard.all_modifiers:
                    if event_type == _nixkeyboard.KEY_DOWN:
                        _nixkeyboard.pressed_modifiers.add(name)
                    else:
                        _nixkeyboard.pressed_modifiers.discard(name)

                is_keypad = scan_code in _nixkeyboard.keypad_scan_codes
                event = _nixkeyboard.KeyboardEvent(
                    event_type=event_type, scan_code=scan_code, name=name,
                    time=time_, device=device_id, is_keypad=is_keypad,
                    modifiers=pressed_modifiers_tuple,
                )

                # If the callback doesn't block the key, we re-inject it
                # ourselves: the grab took it away from the system.
                # A raised exception here must NOT kill the reader thread:
                # swallow it, log it, and keep the loop alive.
                try:
                    block = callback(event)
                except Exception as exc:
                    logger.error(f"Error handling key event: {exc}", exc_info=True)
                    block = True
                if block is not False:
                    device.write_event(_nixcommon.EV_KEY, scan_code, value)

        _nixkeyboard.listen = _passthrough_listen
    except Exception as e:
        logger.warning(f"Could not enable real suppress on Linux: {e}")


_patch_keyboard_linux_real_suppress()


class KeyRule:
    """Represents a single remapping rule"""
    
    __slots__ = ('key_to_replace', 'replacement_key', 'mode', 'enabled', 'toggle_state_active')
    
    def __init__(self, key_to_replace: str, replacement_key: str, mode: str = "hold", enabled: bool = True):
        self.key_to_replace = key_to_replace
        self.replacement_key = replacement_key
        self.mode = mode
        self.enabled = enabled
        self.toggle_state_active = False
        
    def to_dict(self) -> dict:
        """Convert the rule to a dictionary for saving"""
        return {
            "key_to_replace": self.key_to_replace,
            "replacement_key": self.replacement_key,
            "mode": self.mode,
            "enabled": self.enabled
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'KeyRule':
        """Create a rule from a dictionary"""
        return KeyRule(
            data.get("key_to_replace", ""),
            data.get("replacement_key", ""),
            data.get("mode", "hold"),
            data.get("enabled", True)
        )


class KeyHandler:
    """
    Manages key capture and replacement with multiple rules.
    Optimized with a hash map for O(1) lookup.
    """

    def __init__(self, app_monitor):
        self.app_monitor = app_monitor
        self.key_hook = None
        
        # Dual data structure
        self._rules_map: Dict[str, KeyRule] = {}  # For fast O(1) lookup
        self._rules_list: List[KeyRule] = []      # For UI/persistence/order
        
        self._tk_root = None
        self._active_keys = set()  # Prevent recursion
        
        # Performance metrics (optional)
        self._latency_samples = []
        self._last_perf_log = time.time()
        
    def set_tk_root(self, root):
        """Sets the reference to the Tkinter root for thread-safe operations"""
        self._tk_root = root
    
    def add_rule(self, key_to_replace: str, replacement_key: str, 
                 mode: str = "hold", enabled: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Add a new remapping rule.
        
        Returns:
            (success: bool, error_key: Optional[str])
        """
        # Check for circular recursion BEFORE adding
        if self._would_create_cycle(key_to_replace, replacement_key):
            logger.warning(f"Circular cycle detected: {key_to_replace} -> {replacement_key}")
            return False, "error_circular"
        
        rule = KeyRule(key_to_replace, replacement_key, mode, enabled)
        
        # Add to list (creation order)
        self._rules_list.append(rule)
        
        # Add to map only if enabled
        if enabled:
            self._rules_map[key_to_replace] = rule
        
        logger.info(f"Rule added: {key_to_replace} -> {replacement_key} [{mode}]")
        return True, None
    
    def remove_rule(self, index: int) -> bool:
        """Remove a rule by index"""
        if not 0 <= index < len(self._rules_list):
            logger.error(f"Invalid rule index: {index}")
            return False
        
        rule = self._rules_list.pop(index)
        
        # Remove from map if it was there
        if rule.key_to_replace in self._rules_map:
            del self._rules_map[rule.key_to_replace]
        
        logger.info(f"Rule removed: {rule.key_to_replace} -> {rule.replacement_key}")
        return True
    
    def update_rule(self, index: int, key_to_replace: str, replacement_key: str, 
                    mode: str, enabled: bool) -> Tuple[bool, Optional[str]]:
        """Update an existing rule"""
        if not 0 <= index < len(self._rules_list):
            return False, "error_invalid_index"
        
        old_rule = self._rules_list[index]
        
        # Check recursion only if the key changed
        if (old_rule.key_to_replace != key_to_replace or 
            old_rule.replacement_key != replacement_key):
            if self._would_create_cycle(key_to_replace, replacement_key, exclude_index=index):
                return False, "error_circular"
        
        # Remove the old rule from the map
        if old_rule.key_to_replace in self._rules_map:
            del self._rules_map[old_rule.key_to_replace]
        
        # Update rule
        new_rule = KeyRule(key_to_replace, replacement_key, mode, enabled)
        self._rules_list[index] = new_rule
        
        # Add to map if enabled
        if enabled:
            self._rules_map[key_to_replace] = new_rule
        
        logger.info(f"Rule updated [{index}]: {key_to_replace} -> {replacement_key}")
        return True, None
    
    def get_rules(self) -> List[KeyRule]:
        """Get all rules (for UI)"""
        return self._rules_list
    
    def load_rules(self, rules_data: List[dict]):
        """Load rules from saved data"""
        self._rules_list.clear()
        self._rules_map.clear()
        
        for rule_dict in rules_data:
            rule = KeyRule.from_dict(rule_dict)
            self._rules_list.append(rule)
            
            if rule.enabled:
                self._rules_map[rule.key_to_replace] = rule
        
        logger.info(f"Loaded {len(self._rules_list)} rules ({len(self._rules_map)} active)")
    
    def _would_create_cycle(self, key_to_replace: str, replacement_key: str, 
                           exclude_index: Optional[int] = None) -> bool:
        """
        Detects circular remapping cycles using DFS.
        E.g.: A->B, B->C, C->A creates an infinite cycle.
        Uses the internal map directly.
        """
        # Build temporary dependency graph
        graph = {}
        
        for i, rule in enumerate(self._rules_list):
            if exclude_index is not None and i == exclude_index:
                continue
            if rule.key_to_replace not in graph:
                graph[rule.key_to_replace] = []
            graph[rule.key_to_replace].append(rule.replacement_key)
        
        # Add the new rule to the graph
        if key_to_replace not in graph:
            graph[key_to_replace] = []
        graph[key_to_replace].append(replacement_key)
        
        # DFS to detect cycles
        def has_cycle(node: str, visited: set, rec_stack: set) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for node in graph:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    return True
        
        return False

    def handle_key_event(self, e) -> bool:
        """
        Handles all keyboard events captured by the hook.
        O(1) lookup with hash map - minimal latency
        """
        # Latency benchmark (optional)
        start = time.perf_counter() if __debug__ else None
        
        try:
            # Ignore if the target app is not active
            if not self.app_monitor.target_app_is_active:
                return True
            
            # Prevent recursion: if the key is already being processed
            if e.name in self._active_keys:
                return True
            
            # O(1) LOOKUP - The magic is here
            rule = self._rules_map.get(e.name)
            
            if not rule:
                return True  # No rule, let the key through
            
            # Mark key as active to prevent recursion
            self._active_keys.add(e.name)
            
            try:
                # Logic according to the rule's mode
                if rule.mode == 'hold':
                    if e.event_type == keyboard.KEY_DOWN:
                        self._press_key(rule.replacement_key)
                    elif e.event_type == keyboard.KEY_UP:
                        self._release_key(rule.replacement_key)
                
                elif rule.mode == 'toggle':
                    if e.event_type == keyboard.KEY_DOWN:
                        if rule.toggle_state_active:
                            self._release_key(rule.replacement_key)
                            rule.toggle_state_active = False
                        else:
                            self._press_key(rule.replacement_key)
                            rule.toggle_state_active = True
                
                # Block the original key
                return False
                
            finally:
                # Release the key from the active set
                self._active_keys.discard(e.name)
        
        finally:
            # Performance logging (every 1000 events)
            if start and __debug__:
                latency_ms = (time.perf_counter() - start) * 1000
                self._latency_samples.append(latency_ms)
                
                if len(self._latency_samples) >= 1000:
                    avg = sum(self._latency_samples) / len(self._latency_samples)
                    logger.debug(f"Average latency: {avg:.3f}ms (1000 events)")
                    self._latency_samples.clear()

    @staticmethod
    def _reset_replaying_flag():
        """
        keyboard.send() sets _listener.is_replaying = True and resets it to
        False with no try/finally. If the key name is invalid, parse_hotkey
        raises and the flag stays True forever, silently disabling remapping.
        This forces it back to False after an error.
        """
        try:
            listener = getattr(keyboard, '_listener', None)
            if listener is not None:
                listener.is_replaying = False
        except Exception:
            pass

    def _press_key(self, key: str):
        """Safe wrapper around keyboard.press that never breaks the hook."""
        try:
            keyboard.press(key)
        except Exception as e:
            logger.error(f"Failed to press key '{key}': {e}", exc_info=True)
            self._reset_replaying_flag()

    def _release_key(self, key: str):
        """Safe wrapper around keyboard.release that never breaks the hook."""
        try:
            keyboard.release(key)
        except Exception as e:
            logger.error(f"Failed to release key '{key}': {e}", exc_info=True)
            self._reset_replaying_flag()

    def start(self) -> Tuple[bool, Optional[str]]:
        """Start key capture"""
        if self.key_hook:
            return False, "error_hook_active"
        
        if not self._rules_map:
            logger.warning("Attempted to start without active rules")
            return False, "No active rules"
        
        try:
            logger.info(f"Starting hooks with {len(self._rules_map)} active rules")
            self.key_hook = keyboard.hook(self.handle_key_event, suppress=True)
            return True, None
        except ImportError as e:
            logger.error(f"Permission error: {e}")
            return False, "error_admin_required"
        except Exception as e:
            logger.error(f"Unexpected error starting: {e}", exc_info=True)
            return False, f"error_unexpected: {e}"

    def stop(self) -> bool:
        """Stop key capture"""
        if not self.key_hook:
            return False
        
        try:
            keyboard.unhook(self.key_hook)
            self.key_hook = None
            
            # Release all active toggle keys
            for rule in self._rules_list:
                if rule.toggle_state_active:
                    self._release_key(rule.replacement_key)
                    rule.toggle_state_active = False
            
            self._active_keys.clear()
            logger.info("Hooks stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Error stopping hooks: {e}", exc_info=True)
            return False

    def is_active(self) -> bool:
        """Check if the hook is active"""
        return self.key_hook is not None

    def listen_for_key(self, callback):
        """
        Listens for and captures the next pressed key.
        Thread-safe with Tkinter.
        """
        def capture():
            try:
                key = keyboard.read_event(suppress=False)
                while key.event_type != 'down':
                    key = keyboard.read_event(suppress=False)
                
                captured_key = key.name
                logger.debug(f"Key captured: {captured_key}")
                
                if self._tk_root:
                    self._tk_root.after(0, lambda: callback(captured_key, None))
                else:
                    callback(captured_key, None)
                    
            except Exception as e:
                logger.error(f"Error capturing key: {e}", exc_info=True)
                if self._tk_root:
                    self._tk_root.after(0, lambda: callback(None, str(e)))
                else:
                    callback(None, str(e))

        import threading
        thread = threading.Thread(target=capture, daemon=True)
        thread.start()

    # COMPATIBILITY METHODS (To avoid breaking existing code)

    def set_keys(self, key_to_replace: str, replacement_key: str):
        """
        DEPRECATED: Use add_rule() for multiple rules.
        Kept for backward compatibility.
        """
        logger.warning("set_keys() is deprecated. Use add_rule() instead.")
        self._rules_list.clear()
        self._rules_map.clear()
        self.add_rule(key_to_replace, replacement_key, mode="hold", enabled=True)
    
    def set_mode(self, mode: str):
        """
        DEPRECATED: Use update_rule() to configure individual rules.
        """
        logger.warning("set_mode() is deprecated. Use update_rule() instead.")
        for rule in self._rules_list:
            rule.mode = mode