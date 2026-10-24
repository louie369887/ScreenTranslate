import copy
import json
import os
import threading

APP_NAME = "屏幕翻译"
DATA_DIR_NAME = "ScreenTranslator"


def data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    path = os.path.join(base, DATA_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


CONFIG_PATH = os.path.join(data_dir(), "config.json")
HISTORY_PATH = os.path.join(data_dir(), "history.json")
LOG_PATH = os.path.join(data_dir(), "app.log")

TARGET_LANGS = [
    "简体中文",
    "繁體中文",
    "English",
    "日本語",
    "한국어",
    "Français",
    "Deutsch",
    "Español",
    "Русский",
]

DEFAULTS = {
    "first_run": True,
    "theme": "system",
    "close_to_tray": True,
    "autostart": False,
    "hotkey_capture": "ctrl+alt+s",
    "hotkey_fullscreen": "ctrl+alt+f",
    "target_lang": "简体中文",
    "engine": "local",
    "capture.default_mode": "area",
    "local": {
        "model_path": "",
        "auto_load": True,
        "n_gpu_layers": 0,
        "n_ctx": 4096,
        "n_threads": 0,
        "temperature": 0.7,
        "top_p": 0.6,
        "top_k": 20,
        "repeat_penalty": 1.05,
        "max_tokens": 2048,
        "prompt_template": "将以下文本翻译成{target_lang},注意只需要输出翻译后的结果,不要额外解释:\n\n{text}",
    },
    "apis": [],
    "active_api": "",
    "ocr": {
        "scale": "auto",
        "merge_paragraph": True,
        "min_score": 0.5,
    },
    "realtime": {
        "enabled": True,
        "interval_ms": 500,
        "settle_ms": 800,
        "diff_threshold": 6.0,
        "max_runs": 0,
    },
    "display": {
        "opacity": 88,
        "font_size": 14,
        "always_top": True,
        "show_source": False,
        "auto_copy": False,
        "wrap_width": 560,
    },
    "history_limit": 300,
}


def _deep_merge(base, patch):
    out = copy.deepcopy(base)
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self):
        self._lock = threading.RLock()
        self._data = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self):
        with self._lock:
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data = _deep_merge(DEFAULTS, saved)
            except Exception:
                self._data = copy.deepcopy(DEFAULTS)

    def save(self):
        with self._lock:
            tmp = CONFIG_PATH + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
                os.replace(tmp, CONFIG_PATH)
            except Exception:
                pass

    def get(self, key, default=None):
        with self._lock:
            cur = self._data
            for part in key.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return default
            return cur

    def set(self, key, value, save=True):
        with self._lock:
            parts = key.split(".")
            cur = self._data
            for part in parts[:-1]:
                cur = cur.setdefault(part, {})
            cur[parts[-1]] = value
            if save:
                self.save()


_hist_lock = threading.RLock()


def _read_history():
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_history(items):
    try:
        tmp = HISTORY_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
        os.replace(tmp, HISTORY_PATH)
    except Exception:
        pass


def load_history():
    with _hist_lock:
        return _read_history()


def add_history(entry, limit=300):
    with _hist_lock:
        items = _read_history()
        items.insert(0, entry)
        items = items[: max(10, int(limit))]
        _write_history(items)


def clear_history():
    with _hist_lock:
        _write_history([])
