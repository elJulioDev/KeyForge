"""
Manejador de eventos de teclado con soporte de múltiples reglas
"""

import keyboard

class KeyRule:
    """Representa una regla individual de remapeo"""
    
    def __init__(self, key_to_replace, replacement_key, mode="hold", enabled=True):
        self.key_to_replace = key_to_replace
        self.replacement_key = replacement_key
        self.mode = mode
        self.enabled = enabled
        self.toggle_state_active = False
        
    def to_dict(self):
        """Convierte la regla a diccionario para guardar"""
        return {
            "key_to_replace": self.key_to_replace,
            "replacement_key": self.replacement_key,
            "mode": self.mode,
            "enabled": self.enabled
        }
    
    @staticmethod
    def from_dict(data):
        """Crea una regla desde un diccionario"""
        return KeyRule(
            data.get("key_to_replace", ""),
            data.get("replacement_key", ""),
            data.get("mode", "hold"),
            data.get("enabled", True)
        )


class KeyHandler:
    """Gestiona la captura y reemplazo de teclas con múltiples reglas"""

    def __init__(self, app_monitor):
        self.app_monitor = app_monitor
        self.key_hook = None
        self.rules = []  # Lista de KeyRule
        self.is_listening = False
        self._tk_root = None
        self._active_keys = set()  # Prevenir recursión
        
    def set_tk_root(self, root):
        """Establece la referencia al root de Tkinter para operaciones thread-safe"""
        self._tk_root = root
    
    def add_rule(self, key_to_replace, replacement_key, mode="hold", enabled=True):
        """Agrega una nueva regla de remapeo"""
        # Verificar recursión circular
        if self._would_create_cycle(key_to_replace, replacement_key):
            return False, "Recursión circular detectada"
        
        rule = KeyRule(key_to_replace, replacement_key, mode, enabled)
        self.rules.append(rule)
        return True, None
    
    def remove_rule(self, index):
        """Elimina una regla por índice"""
        if 0 <= index < len(self.rules):
            self.rules.pop(index)
            return True
        return False
    
    def update_rule(self, index, key_to_replace, replacement_key, mode, enabled):
        """Actualiza una regla existente"""
        if 0 <= index < len(self.rules):
            # Verificar recursión solo si cambió la tecla
            old_rule = self.rules[index]
            if (old_rule.key_to_replace != key_to_replace or 
                old_rule.replacement_key != replacement_key):
                if self._would_create_cycle(key_to_replace, replacement_key, exclude_index=index):
                    return False, "Recursión circular detectada"
            
            self.rules[index] = KeyRule(key_to_replace, replacement_key, mode, enabled)
            return True, None
        return False, "Índice inválido"
    
    def get_rules(self):
        """Obtiene todas las reglas"""
        return self.rules
    
    def load_rules(self, rules_data):
        """Carga reglas desde datos guardados"""
        self.rules = [KeyRule.from_dict(r) for r in rules_data]
    
    def _would_create_cycle(self, key_to_replace, replacement_key, exclude_index=None):
        """
        Detecta ciclos de remapeo circulares.
        Ej: A->B, B->C, C->A crea un ciclo infinito.
        """
        # Construir grafo de dependencias
        graph = {}
        for i, rule in enumerate(self.rules):
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
        def has_cycle(node, visited, rec_stack):
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

    def handle_key_event(self, e):
        """
        Maneja todos los eventos de teclado capturados por el hook.
        Soporta múltiples reglas simultáneas.
        """
        # Ignorar si la app objetivo no está activa
        if not self.app_monitor.target_app_is_active:
            return True
        
        # Prevenir recursión: si la tecla ya está siendo procesada, ignorar
        if e.name in self._active_keys:
            return True
        
        # Buscar regla que coincida
        matching_rule = None
        for rule in self.rules:
            if rule.enabled and rule.key_to_replace == e.name:
                matching_rule = rule
                break
        
        if not matching_rule:
            return True  # No hay regla, dejar pasar la tecla
        
        # Marcar tecla como activa para prevenir recursión
        self._active_keys.add(e.name)
        
        try:
            # Lógica según el modo de la regla
            if matching_rule.mode == 'hold':
                if e.event_type == keyboard.KEY_DOWN:
                    keyboard.press(matching_rule.replacement_key)
                elif e.event_type == keyboard.KEY_UP:
                    keyboard.release(matching_rule.replacement_key)
            
            elif matching_rule.mode == 'toggle':
                if e.event_type == keyboard.KEY_DOWN:
                    if matching_rule.toggle_state_active:
                        keyboard.release(matching_rule.replacement_key)
                        matching_rule.toggle_state_active = False
                    else:
                        keyboard.press(matching_rule.replacement_key)
                        matching_rule.toggle_state_active = True
            
            # Bloquear la tecla original
            return False
            
        finally:
            # Liberar la tecla del conjunto activo
            self._active_keys.discard(e.name)

    def start(self):
        """Inicia la captura de teclas"""
        if not self.key_hook:
            try:
                self.key_hook = keyboard.hook(self.handle_key_event, suppress=True)
                return True, None
            except ImportError:
                return False, "Se requieren permisos de Administrador (root)"
            except Exception as e:
                return False, f"Error inesperado: {e}"
        return False, "Hook ya está activo"

    def stop(self):
        """Detiene la captura de teclas"""
        if self.key_hook:
            keyboard.unhook(self.key_hook)
            self.key_hook = None
            
            # Liberar todas las teclas toggle activas
            for rule in self.rules:
                if rule.toggle_state_active:
                    keyboard.release(rule.replacement_key)
                    rule.toggle_state_active = False
            
            self._active_keys.clear()
            return True
        return False

    def is_active(self):
        """Verifica si el hook está activo"""
        return self.key_hook is not None

    def listen_for_key(self, callback):
        """
        Escucha y captura la siguiente tecla presionada.
        Thread-safe con Tkinter.
        """
        if self.is_listening:
            return

        self.is_listening = True

        def capture():
            try:
                key = keyboard.read_event(suppress=False)
                while key.event_type != 'down':
                    key = keyboard.read_event(suppress=False)
                
                captured_key = key.name
                
                if self._tk_root:
                    self._tk_root.after(0, lambda: callback(captured_key, None))
                else:
                    callback(captured_key, None)
                    
            except Exception as e:
                if self._tk_root:
                    self._tk_root.after(0, lambda: callback(None, str(e)))
                else:
                    callback(None, str(e))
            finally:
                self.is_listening = False

        import threading
        thread = threading.Thread(target=capture, daemon=True)
        thread.start()

    # MÉTODOS DE COMPATIBILIDAD (Deprecados)

    def set_keys(self, key_to_replace, replacement_key):
        """
        DEPRECADO: Configura una regla única (compatibilidad con versión anterior).
        Usa add_rule() para múltiples reglas.
        """
        # Limpiar reglas existentes y crear una nueva
        self.rules.clear()
        self.add_rule(key_to_replace, replacement_key, mode="hold", enabled=True)
    
    def set_mode(self, mode):
        """
        DEPRECADO: Establece el modo de todas las reglas.
        Usa update_rule() para configurar reglas individuales.
        """
        for rule in self.rules:
            rule.mode = mode
