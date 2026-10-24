import os
import threading

from PySide6.QtCore import QObject, Signal

from app.config import DEFAULTS
from app.translate import local_llm, openai_api

DEFAULT_PROMPT = DEFAULTS["local"]["prompt_template"]


def build_prompt(template, target, text):
    t = template or DEFAULT_PROMPT
    return t.replace("{target_lang}", target or "简体中文").replace("{text}", text)


class Translator(QObject):
    loadStateChanged = Signal(str, int)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self._llm = None
        self._llm_lock = threading.Lock()
        self._loading = False

    def local_ready(self):
        return self._llm is not None

    def local_loading(self):
        return self._loading

    def load_local_async(self):
        if self._loading:
            return
        path = self.cfg.get("local.model_path", "")
        if not path:
            self.loadStateChanged.emit("未选择本地模型文件", 2)
            return
        if not os.path.isfile(path):
            self.loadStateChanged.emit(f"模型文件不存在: {path}", 2)
            return
        if self._llm is not None and getattr(self._llm, "_model_path", None) == path:
            self.loadStateChanged.emit("本地模型已就绪", 1)
            return
        self._loading = True
        self.loadStateChanged.emit("正在加载本地模型，请稍候…", 0)

        def run():
            try:
                llm = local_llm.load(
                    model_path=path,
                    n_ctx=self.cfg.get("local.n_ctx", 4096),
                    n_gpu_layers=self.cfg.get("local.n_gpu_layers", 0),
                    n_threads=self.cfg.get("local.n_threads", 0),
                )
                setattr(llm, "_model_path", path)
                with self._llm_lock:
                    old = self._llm
                    self._llm = llm
                del old
                self.loadStateChanged.emit("本地模型已就绪", 1)
            except Exception as e:
                self.loadStateChanged.emit(f"模型加载失败: {e}", 2)
            finally:
                self._loading = False

        threading.Thread(target=run, daemon=True).start()

    def unload_local(self):
        with self._llm_lock:
            self._llm = None
        self.loadStateChanged.emit("本地模型已卸载", 0)

    def translate(self, text):
        engine = self.cfg.get("engine", "local")
        target = self.cfg.get("target_lang", "简体中文")
        prompt = build_prompt(self.cfg.get("local.prompt_template"), target, text)
        if engine == "api":
            return openai_api.translate(self.cfg, prompt)
        if self._llm is None:
            if not self._loading:
                self.load_local_async()
            return False, "", "本地模型尚未加载，可在设置中等待加载或切换到 API"
        params = {
            "max_tokens": self.cfg.get("local.max_tokens", 2048),
            "temperature": self.cfg.get("local.temperature", 0.7),
            "top_p": self.cfg.get("local.top_p", 0.6),
            "top_k": self.cfg.get("local.top_k", 20),
            "repeat_penalty": self.cfg.get("local.repeat_penalty", 1.05),
        }
        try:
            with self._llm_lock:
                out = local_llm.generate(self._llm, prompt, params)
            if not out:
                return False, "", "模型返回为空"
            return True, out, ""
        except Exception as e:
            return False, "", str(e)
