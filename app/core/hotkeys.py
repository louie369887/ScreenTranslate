import threading


class HotkeyManager:
    def __init__(self):
        self._handles = []
        self._lock = threading.Lock()

    def apply(self, bindings):
        self.unregister_all()
        errors = []
        with self._lock:
            try:
                import keyboard
            except Exception as e:
                return [f"无法加载全局热键模块:{e}"]
            for combo, cb in bindings.items():
                combo = (combo or "").strip().lower()
                if not combo:
                    continue
                try:
                    h = keyboard.add_hotkey(combo, cb, suppress=False)
                    self._handles.append(h)
                except Exception as e:
                    errors.append(f"{combo}: {e}")
        return errors

    def unregister_all(self):
        with self._lock:
            try:
                import keyboard
            except Exception:
                self._handles = []
                return
            for h in self._handles:
                try:
                    keyboard.remove_hotkey(h)
                except Exception:
                    pass
            self._handles = []
