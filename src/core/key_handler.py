"""
Manejador de eventos de teclado con búsqueda O(1)
Optimizado para latencia mínima
"""

import keyboard
import time
import sys
import os
from typing import Dict, List, Optional, Tuple

# Logger profesional (se importará del módulo utils)
try:
    from ..utils.logger import get_logger
    logger = get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


def _patch_keyboard_linux_root_check():
    """
    keyboard._nixcommon.ensure_root() exige os.geteuid() == 0 sin mirar
    los permisos reales de /dev/uinput. Con la regla udev + grupo 'input'
    (ver README), el acceso real ya existe aunque no seamos root — el
    chequeo de la librería es innecesariamente estricto para ese caso.
    Lo reemplazamos por uno que valida acceso real al dispositivo.
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
                "Sin acceso a /dev/uinput. Falta el grupo 'input' o la regla "
                "udev (ver README, sección 'Linux permissions'), o falta "
                "cerrar sesión tras agregarte al grupo."
            )

        # _nixkeyboard hizo "from ._nixcommon import ensure_root" al importarse,
        # queda un nombre propio en su namespace. Parchear solo _nixcommon no
        # lo toca; hay que parchear ambos.
        _nixcommon.ensure_root = _ensure_device_access
        _nixkeyboard.ensure_root = _ensure_device_access
    except Exception as e:
        logger.warning(f"No se pudo parchear el chequeo de root de 'keyboard': {e}")


_patch_keyboard_linux_root_check()


def _patch_keyboard_dumpkeys_cache():
    """
    'dumpkeys' necesita un descriptor de consola real (VT), algo que no
    existe dentro de una terminal gráfica (Konsole/Wayland/X11). Ahí
    falla con "Couldn't get a file descriptor referring to the console",
    incluso teniendo permisos sobre /dev/input y /dev/uinput — es una
    restricción del kernel (CAP_SYS_TTY_CONFIG), no arreglable con udev.

    Solución: cachear la salida de 'dumpkeys' una sola vez (generada con
    sudo, o desde una TTY real con Ctrl+Alt+F3) y servirla desde disco en
    cada arranque normal, sin volver a invocar el binario.
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
                # Primer intento: probar el binario real (root o TTY real)
                # y, si funciona, guardar el resultado para la próxima vez.
                output = original_check_output(cmd, *args, **kwargs)
                cache_dir.mkdir(parents=True, exist_ok=True)
                path.write_text(output, encoding='utf-8')
                return output
            return original_check_output(cmd, *args, **kwargs)

        _nixkeyboard.check_output = _cached_check_output
    except Exception as e:
        logger.warning(f"No se pudo activar la caché de 'dumpkeys': {e}")


_patch_keyboard_dumpkeys_cache()


def _patch_keyboard_linux_real_suppress():
    """
    La librería 'keyboard' documenta (README propio): "Key
    suppression/blocking only available on Windows". En Linux
    _nixkeyboard.listen() lee /dev/input/eventN de forma pasiva y
    descarta el valor de retorno del callback -> la tecla original
    SIEMPRE llega al sistema, sin importar si hay una regla que la
    reemplaza. Resultado: "A"->"S" escribe "AS", no "S".

    Fix real (lo que en Windows hace el driver, aquí lo hacemos a mano):
      1. EVIOCGRAB sobre cada dispositivo físico de teclado: deja de
         entregarle eventos a nadie más (Wayland/X11 incluidos).
      2. Reinyectamos por el dispositivo virtual (uinput) toda tecla
         que el callback NO bloquee, para no perder el resto del teclado.

    De paso, evita el `exit()` que la librería llama dentro del hilo de
    lectura cuando un dispositivo da "Permission denied" (p.ej. algún
    evento ACPI tipo botón de energía sin acceso): ahora ese dispositivo
    simplemente se ignora en vez de imprimir el aviso y matar su hilo.
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
                        logger.warning(f"Sin acceso a {self.path}, se ignora ese dispositivo.")
                    else:
                        logger.warning(f"No se pudo abrir {self.path}: {e}")
                    return None

                if self.path != 'uinput Fake Device':
                    try:
                        fcntl.ioctl(self._input_file, EVIOCGRAB, 1)
                    except OSError as e:
                        logger.warning(f"No se pudo reservar {self.path} (EVIOCGRAB): {e}")

                import atexit as _atexit
                def try_close():
                    try:
                        self._input_file.close()
                    except Exception:
                        pass
                _atexit.register(try_close)
            return self._input_file

        _nixcommon.EventDevice.input_file = property(_safe_grabbed_input_file)

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

                # Si el callback no bloquea la tecla, la reinyectamos
                # nosotros mismos: el grab se la quitó al sistema.
                if callback(event) is not False:
                    device.write_event(_nixcommon.EV_KEY, scan_code, value)

        _nixkeyboard.listen = _passthrough_listen
    except Exception as e:
        logger.warning(f"No se pudo activar el suppress real en Linux: {e}")


_patch_keyboard_linux_real_suppress()


class KeyRule:
    """Representa una regla individual de remapeo"""
    
    __slots__ = ('key_to_replace', 'replacement_key', 'mode', 'enabled', 'toggle_state_active')
    
    def __init__(self, key_to_replace: str, replacement_key: str, mode: str = "hold", enabled: bool = True):
        self.key_to_replace = key_to_replace
        self.replacement_key = replacement_key
        self.mode = mode
        self.enabled = enabled
        self.toggle_state_active = False
        
    def to_dict(self) -> dict:
        """Convierte la regla a diccionario para guardar"""
        return {
            "key_to_replace": self.key_to_replace,
            "replacement_key": self.replacement_key,
            "mode": self.mode,
            "enabled": self.enabled
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'KeyRule':
        """Crea una regla desde un diccionario"""
        return KeyRule(
            data.get("key_to_replace", ""),
            data.get("replacement_key", ""),
            data.get("mode", "hold"),
            data.get("enabled", True)
        )


class KeyHandler:
    """
    Gestiona la captura y reemplazo de teclas con múltiples reglas.
    Optimizado con hash map para búsqueda O(1).
    """

    def __init__(self, app_monitor):
        self.app_monitor = app_monitor
        self.key_hook = None
        
        # Doble estructura de datos
        self._rules_map: Dict[str, KeyRule] = {}  # Para búsqueda O(1) rápida
        self._rules_list: List[KeyRule] = []      # Para UI/persistencia/orden
        
        self._tk_root = None
        self._active_keys = set()  # Prevenir recursión
        
        # Métricas de rendimiento (opcional)
        self._latency_samples = []
        self._last_perf_log = time.time()
        
    def set_tk_root(self, root):
        """Establece la referencia al root de Tkinter para operaciones thread-safe"""
        self._tk_root = root
    
    def add_rule(self, key_to_replace: str, replacement_key: str, 
                 mode: str = "hold", enabled: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Agrega una nueva regla de remapeo.
        
        Returns:
            (success: bool, error_key: Optional[str])
        """
        # Verificar recursión circular ANTES de agregar
        if self._would_create_cycle(key_to_replace, replacement_key):
            logger.warning(f"Ciclo circular detectado: {key_to_replace} -> {replacement_key}")
            return False, "error_circular"
        
        rule = KeyRule(key_to_replace, replacement_key, mode, enabled)
        
        # Agregar a lista (orden de creación)
        self._rules_list.append(rule)
        
        # Agregar al mapa solo si está habilitada
        if enabled:
            self._rules_map[key_to_replace] = rule
        
        logger.info(f"Regla agregada: {key_to_replace} -> {replacement_key} [{mode}]")
        return True, None
    
    def remove_rule(self, index: int) -> bool:
        """Elimina una regla por índice"""
        if not 0 <= index < len(self._rules_list):
            logger.error(f"Índice de regla inválido: {index}")
            return False
        
        rule = self._rules_list.pop(index)
        
        # Remover del mapa si estaba ahí
        if rule.key_to_replace in self._rules_map:
            del self._rules_map[rule.key_to_replace]
        
        logger.info(f"Regla eliminada: {rule.key_to_replace} -> {rule.replacement_key}")
        return True
    
    def update_rule(self, index: int, key_to_replace: str, replacement_key: str, 
                    mode: str, enabled: bool) -> Tuple[bool, Optional[str]]:
        """Actualiza una regla existente"""
        if not 0 <= index < len(self._rules_list):
            return False, "error_invalid_index"
        
        old_rule = self._rules_list[index]
        
        # Verificar recursión solo si cambió la tecla
        if (old_rule.key_to_replace != key_to_replace or 
            old_rule.replacement_key != replacement_key):
            if self._would_create_cycle(key_to_replace, replacement_key, exclude_index=index):
                return False, "error_circular"
        
        # Remover la regla antigua del mapa
        if old_rule.key_to_replace in self._rules_map:
            del self._rules_map[old_rule.key_to_replace]
        
        # Actualizar regla
        new_rule = KeyRule(key_to_replace, replacement_key, mode, enabled)
        self._rules_list[index] = new_rule
        
        # Agregar al mapa si está habilitada
        if enabled:
            self._rules_map[key_to_replace] = new_rule
        
        logger.info(f"Regla actualizada [{index}]: {key_to_replace} -> {replacement_key}")
        return True, None
    
    def get_rules(self) -> List[KeyRule]:
        """Obtiene todas las reglas (para UI)"""
        return self._rules_list
    
    def load_rules(self, rules_data: List[dict]):
        """Carga reglas desde datos guardados"""
        self._rules_list.clear()
        self._rules_map.clear()
        
        for rule_dict in rules_data:
            rule = KeyRule.from_dict(rule_dict)
            self._rules_list.append(rule)
            
            if rule.enabled:
                self._rules_map[rule.key_to_replace] = rule
        
        logger.info(f"Cargadas {len(self._rules_list)} reglas ({len(self._rules_map)} activas)")
    
    def _would_create_cycle(self, key_to_replace: str, replacement_key: str, 
                           exclude_index: Optional[int] = None) -> bool:
        """
        Detecta ciclos de remapeo circulares usando DFS.
        Ej: A->B, B->C, C->A crea un ciclo infinito.
        Usa el mapa interno directamente.
        """
        # Construir grafo temporal de dependencias
        graph = {}
        
        for i, rule in enumerate(self._rules_list):
            if exclude_index is not None and i == exclude_index:
                continue
            if rule.key_to_replace not in graph:
                graph[rule.key_to_replace] = []
            graph[rule.key_to_replace].append(rule.replacement_key)
        
        # Agregar la nueva regla al grafo
        if key_to_replace not in graph:
            graph[key_to_replace] = []
        graph[key_to_replace].append(replacement_key)
        
        # DFS para detectar ciclos
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
        Maneja todos los eventos de teclado capturados por el hook.
        Búsqueda O(1) con hash map - latencia mínima
        """
        # Benchmark de latencia (opcional)
        start = time.perf_counter() if __debug__ else None
        
        try:
            # Ignorar si la app objetivo no está activa
            if not self.app_monitor.target_app_is_active:
                return True
            
            # Prevenir recursión: si la tecla ya está siendo procesada
            if e.name in self._active_keys:
                return True
            
            # BÚSQUEDA O(1) - La magia está aquí
            rule = self._rules_map.get(e.name)
            
            if not rule:
                return True  # No hay regla, dejar pasar la tecla
            
            # Marcar tecla como activa para prevenir recursión
            self._active_keys.add(e.name)
            
            try:
                # Lógica según el modo de la regla
                if rule.mode == 'hold':
                    if e.event_type == keyboard.KEY_DOWN:
                        keyboard.press(rule.replacement_key)
                    elif e.event_type == keyboard.KEY_UP:
                        keyboard.release(rule.replacement_key)
                
                elif rule.mode == 'toggle':
                    if e.event_type == keyboard.KEY_DOWN:
                        if rule.toggle_state_active:
                            keyboard.release(rule.replacement_key)
                            rule.toggle_state_active = False
                        else:
                            keyboard.press(rule.replacement_key)
                            rule.toggle_state_active = True
                
                # Bloquear la tecla original
                return False
                
            finally:
                # Liberar la tecla del conjunto activo
                self._active_keys.discard(e.name)
        
        finally:
            # Logging de rendimiento (cada 1000 eventos)
            if start and __debug__:
                latency_ms = (time.perf_counter() - start) * 1000
                self._latency_samples.append(latency_ms)
                
                if len(self._latency_samples) >= 1000:
                    avg = sum(self._latency_samples) / len(self._latency_samples)
                    logger.debug(f"Latencia promedio: {avg:.3f}ms (1000 eventos)")
                    self._latency_samples.clear()

    def start(self) -> Tuple[bool, Optional[str]]:
        """Inicia la captura de teclas"""
        if self.key_hook:
            return False, "error_hook_active"
        
        if not self._rules_map:
            logger.warning("Intento de iniciar sin reglas activas")
            return False, "No active rules"
        
        try:
            logger.info(f"Iniciando hooks con {len(self._rules_map)} reglas activas")
            self.key_hook = keyboard.hook(self.handle_key_event, suppress=True)
            return True, None
        except ImportError as e:
            logger.error(f"Error de permisos: {e}")
            return False, "error_admin_required"
        except Exception as e:
            logger.error(f"Error inesperado al iniciar: {e}", exc_info=True)
            return False, f"error_unexpected: {e}"

    def stop(self) -> bool:
        """Detiene la captura de teclas"""
        if not self.key_hook:
            return False
        
        try:
            keyboard.unhook(self.key_hook)
            self.key_hook = None
            
            # Liberar todas las teclas toggle activas
            for rule in self._rules_list:
                if rule.toggle_state_active:
                    keyboard.release(rule.replacement_key)
                    rule.toggle_state_active = False
            
            self._active_keys.clear()
            logger.info("Hooks detenidos correctamente")
            return True
        except Exception as e:
            logger.error(f"Error al detener hooks: {e}", exc_info=True)
            return False

    def is_active(self) -> bool:
        """Verifica si el hook está activo"""
        return self.key_hook is not None

    def listen_for_key(self, callback):
        """
        Escucha y captura la siguiente tecla presionada.
        Thread-safe con Tkinter.
        """
        def capture():
            try:
                key = keyboard.read_event(suppress=False)
                while key.event_type != 'down':
                    key = keyboard.read_event(suppress=False)
                
                captured_key = key.name
                logger.debug(f"Tecla capturada: {captured_key}")
                
                if self._tk_root:
                    self._tk_root.after(0, lambda: callback(captured_key, None))
                else:
                    callback(captured_key, None)
                    
            except Exception as e:
                logger.error(f"Error capturando tecla: {e}", exc_info=True)
                if self._tk_root:
                    self._tk_root.after(0, lambda: callback(None, str(e)))
                else:
                    callback(None, str(e))

        import threading
        thread = threading.Thread(target=capture, daemon=True)
        thread.start()

    # MÉTODOS DE COMPATIBILIDAD (Para no romper código existente)

    def set_keys(self, key_to_replace: str, replacement_key: str):
        """
        DEPRECADO: Usa add_rule() para múltiples reglas.
        Mantenido por retrocompatibilidad.
        """
        logger.warning("set_keys() está deprecado. Usa add_rule() en su lugar.")
        self._rules_list.clear()
        self._rules_map.clear()
        self.add_rule(key_to_replace, replacement_key, mode="hold", enabled=True)
    
    def set_mode(self, mode: str):
        """
        DEPRECADO: Usa update_rule() para configurar reglas individuales.
        """
        logger.warning("set_mode() está deprecado. Usa update_rule() en su lugar.")
        for rule in self._rules_list:
            rule.mode = mode