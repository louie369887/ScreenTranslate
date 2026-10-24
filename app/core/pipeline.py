import queue
import re
import threading
import time

from PySide6.QtCore import QObject, QRect, Signal

from app.core import capture, win_tools
from app.ocr.engine import OcrEngine
from app.ui import theme
from app.ui.overlay import CaptureOverlay
from app.ui.result_window import ResultWindow


class ScreenTranslator(QObject):
    requestCapture = Signal()
    requestFullCapture = Signal()

    def __init__(self, cfg, translator, ocr, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.translator = translator
        self.ocr = ocr
        self.requestCapture.connect(self._start_overlay)
        self.requestFullCapture.connect(self._start_full)
        self._overlay = None
        self._window = None
        self._region = None
        self._mon_stop = threading.Event()
        self._work_stop = threading.Event()
        self._paused = threading.Event()
        self._jobs = queue.Queue()
        self._mon_thread = None
        self._work_thread = None
        self._last_source = None
        self._run_count = 0

    def _screen_under_cursor(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QCursor
        pos = QCursor.pos()
        scr = QApplication.screenAt(pos)
        if scr is None:
            scr = QApplication.primaryScreen()
        return scr

    def _start_overlay(self):
        if self._overlay is not None:
            return
        scr = self._screen_under_cursor()
        if scr is None:
            return
        ov = CaptureOverlay(self.cfg, scr)
        ov.selected.connect(self._on_overlay_selected)
        ov.cancelled.connect(self._on_overlay_cancelled)
        self._overlay = ov
        ov.show()

    def _on_overlay_selected(self, phys_rect):
        self._overlay = None
        if isinstance(phys_rect, QRect):
            self._begin_session(phys_rect)

    def _on_overlay_cancelled(self):
        self._overlay = None

    def _start_full(self):
        scr = self._screen_under_cursor()
        if scr is None:
            return
        geo = scr.geometry()
        try:
            dpr = float(scr.devicePixelRatio() or 1.0)
        except Exception:
            dpr = 1.0
        phys = QRect(
            round(geo.x() * dpr), round(geo.y() * dpr),
            round(geo.width() * dpr), round(geo.height() * dpr),
        )
        self._begin_session(phys)

    def _begin_session(self, phys_rect):
        self.stop_session()
        self._region = (phys_rect.x(), phys_rect.y(), phys_rect.width(), phys_rect.height())
        self._run_count = 0
        self._last_source = None
        cfg = self.cfg
        win = ResultWindow(cfg)
        scr = self._screen_under_cursor()
        if scr:
            win.place_for_region(phys_rect, scr)
        win.closedByUser.connect(self.stop_session)
        win.retryClicked.connect(self._retry)
        win.liveToggled.connect(self._toggle_live)
        win.set_live(cfg.get("realtime.enabled", True))
        if not cfg.get("realtime.enabled", True):
            self._paused.set()
        win.show()
        self._window = win
        self._mon_stop.clear()
        self._work_stop.clear()
        self._mon_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._mon_thread.start()
        self._work_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._work_thread.start()
        self._submit_job(self._region)

    def _retry(self):
        self._last_source = None
        self._submit_job(self._region)

    def _toggle_live(self, on):
        if on:
            self._paused.clear()
        else:
            self._paused.set()

    def _submit_job(self, region):
        try:
            self._jobs.put_nowait(region)
        except queue.Full:
            pass

    def _monitor_loop(self):
        cfg = self.cfg
        interval = cfg.get("realtime.interval_ms", 500) / 1000.0
        settle = cfg.get("realtime.settle_ms", 800) / 1000.0
        thr = cfg.get("realtime.diff_threshold", 6.0)
        max_runs = cfg.get("realtime.max_runs", 0)
        region = self._region
        ref_thumb = None
        last_motion = time.time()
        ref = None
        try:
            img = capture.grab_region(*region)
            ref = img.copy()
            ref_thumb = img.copy()
        except Exception:
            pass
        while not self._mon_stop.is_set():
            if self._paused.is_set():
                time.sleep(0.2)
                continue
            self._mon_stop.wait(interval)
            if self._mon_stop.is_set():
                break
            if max_runs > 0 and self._run_count >= max_runs:
                self._post_status("已达到最大自动翻译次数", "idle")
                break
            try:
                cur = capture.grab_region(*region)
            except Exception:
                continue
            r = capture.diff_ratio(ref_thumb, cur)
            now = time.time()
            if r > thr:
                last_motion = now
                if self._window:
                    self._window.set_status("busy", "画面变化中...")
            elif now - last_motion >= settle:
                if r > 1.0 or ref_thumb is None:
                    self._submit_job(region)
                    ref_thumb = cur.copy()
                    last_motion = now
                else:
                    pass

    def _worker_loop(self):
        while not self._work_stop.is_set():
            try:
                item = self._jobs.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None:
                break
            while True:
                try:
                    nxt = self._jobs.get_nowait()
                    if nxt is None:
                        return
                    item = nxt
                except queue.Empty:
                    break
            self._process(item)

    def _process(self, region):
        if self._work_stop.is_set():
            return
        self._post_status("busy", "正在识别文字...")
        try:
            img = capture.grab_region(*region)
        except Exception as e:
            self._post_status("err", f"截屏失败: {e}")
            return
        try:
            text, count = self.ocr.recognize(img)
        except Exception as e:
            self._post_status("err", f"OCR 失败: {e}")
            return
        if not text or not text.strip():
            self._post_status("idle", "未检测到文字")
            return
        norm = re.sub(r"\s+", "", text)
        if norm == self._last_source:
            self._post_status("idle", "内容未变化")
            return
        self._post_status("busy", "正在翻译...")
        ok, out, err = self.translator.translate(text)
        if self._work_stop.is_set():
            return
        if ok:
            self._last_source = norm
            self._run_count += 1
            if self._window:
                self._window.set_result(text, out)
                self._window.set_status("ok", "翻译完成")
            from app.config import add_history
            import datetime
            add_history({
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": text[:500],
                "result": out[:500],
            }, self.cfg.get("history_limit", 300))
        else:
            self._post_status("err", f"翻译失败: {err}")

    def _post_status(self, kind, text):
        if self._window:
            self._window.set_status(kind, text)

    def stop_session(self):
        self._mon_stop.set()
        self._work_stop.set()
        self._paused.clear()
        try:
            self._jobs.put_nowait(None)
        except Exception:
            pass
        if self._mon_thread and self._mon_thread.is_alive():
            self._mon_thread.join(timeout=1.5)
        if self._work_thread and self._work_thread.is_alive():
            self._work_thread.join(timeout=1.5)
        self._mon_thread = None
        self._work_thread = None
        win = self._window
        self._window = None
        if win is not None:
            try:
                win.shutdown()
            except Exception:
                pass

    def shutdown(self):
        if self._overlay:
            try:
                self._overlay.close()
            except Exception:
                pass
            self._overlay = None
        self.stop_session()
