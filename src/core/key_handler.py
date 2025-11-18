"""
Manejador de eventos de teclado
"""
import keyboard

class KeyHandler:
    """Gestiona la captura y reemplazo de teclas"""

    def __init__(self, app_monitor):
        self.app_monitor = app_monitor
        self.key_hook = None
        self.toggle_state_active = False
        self.current_mode = "mantener"
        self.key_to_replace = "alt"
        self.replacement_key = "shift"
        self.is_listening = False
        self._tk_root = None  # Referencia al root de Tkinter

    def set_tk_root(self, root):
        """Establece la referencia al root de Tkinter para operaciones thread-safe"""
        self._tk_root = root

    def set_keys(self, key_to_replace, replacement_key):
        """Configura las teclas a reemplazar"""
        self.key_to_replace = key_to_replace
        self.replacement_key = replacement_key

    def set_mode(self, mode):
        """Establece el modo de operación (mantener/intercalar)"""
        self.current_mode = mode

    def handle_key_event(self, e):
        """
        Maneja todos los eventos de teclado capturados por el hook.
        """
        # Ignorar si no es la tecla configurada o si la app objetivo no está activa
        if e.name != self.key_to_replace or not self.app_monitor.target_app_is_active:
            return True

        # Lógica según el modo
        if self.current_mode == 'mantener':
            if e.event_type == keyboard.KEY_DOWN:
                keyboard.press(self.replacement_key)
            elif e.event_type == keyboard.KEY_UP:
                keyboard.release(self.replacement_key)
        elif self.current_mode == 'intercalar':
            if e.event_type == keyboard.KEY_DOWN:
                if self.toggle_state_active:
                    keyboard.release(self.replacement_key)
                    self.toggle_state_active = False
                else:
                    keyboard.press(self.replacement_key)
                    self.toggle_state_active = True

        # Retornar False bloquea la tecla original
        return False

    def start(self):
            """Inicia la captura de teclas controlando errores de permisos"""
            if not self.key_hook:
                try:
                    self.key_hook = keyboard.hook(self.handle_key_event, suppress=True)
                    return True
                except ImportError:
                    # Esto ocurre comúnmente en Linux si no eres root
                    print("❌ Error: Se requieren permisos de Administrador (root) para capturar teclas.")
                    return False
                except Exception as e:
                    print(f"❌ Error inesperado al iniciar hook: {e}")
                    return False
            return False

    def stop(self):
        """Detiene la captura de teclas"""
        if self.key_hook:
            keyboard.unhook(self.key_hook)
            self.key_hook = None
            if self.toggle_state_active:
                keyboard.release(self.replacement_key)
                self.toggle_state_active = False
            return True
        return False

    def is_active(self):
        """Verifica si el hook está activo"""
        return self.key_hook is not None

    def listen_for_key(self, callback):
        """
        Escucha y captura la siguiente tecla presionada.
        
        Args:
            callback: Función que se llamará con la tecla capturada
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
                
                # THREAD-SAFE: Programar el callback en el hilo principal de Tkinter
                if self._tk_root:
                    self._tk_root.after(0, lambda: callback(captured_key, None))
                else:
                    # Fallback si no hay root configurado
                    callback(captured_key, None)
                    
            except Exception as e:
                # THREAD-SAFE: Programar el callback de error en el hilo principal
                if self._tk_root:
                    self._tk_root.after(0, lambda: callback(None, str(e)))
                else:
                    callback(None, str(e))
            finally:
                self.is_listening = False

        import threading
        thread = threading.Thread(target=capture, daemon=True)
        thread.start()
