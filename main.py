import os
import sys
import traceback

from PySide6.QtCore import QSharedMemory, Qt
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from app.config import Config, LOG_PATH
from app.core.capture import ensure_dpi_awareness as _unused_dpi
from app.core.hotkeys import HotkeyManager
from app.core.pipeline import ScreenTranslator
from app.core.win_tools import ensure_dpi_awareness, get_autostart, set_autostart
from app.ocr.engine import OcrEngine
from app.translate.service import Translator
from app.ui import theme
from app.ui.icons import app_icon, app_pixmap
from app.ui.main_window import MainWindow


def excepthook(tp, val, tb):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{'='*60}\n")
            f.write(f"Exception: {tp.__name__}: {val}\n")
            f.write("".join(traceback.format_exception(tp, val, tb)))
            f.write("\n")
    except Exception:
        pass


sys.excepthook = excepthook

ensure_dpi_awareness()

app = QApplication(sys.argv)
app.setApplicationName("屏幕翻译")
app.setQuitOnLastWindowClosed(False)

shared = QSharedMemory("ScreenTranslator.SingleInstance")
if not shared.create(1):
    QMessageBox.information(None, "屏幕翻译", "程序已在运行，请查看系统托盘。")
    sys.exit(0)

icon = app_icon()
app.setWindowIcon(icon)

cfg = Config()
theme.apply(app, cfg)

translator = Translator(cfg)
ocr_engine = OcrEngine(cfg)
pipeline = ScreenTranslator(cfg, translator, ocr_engine)
hotkeys = HotkeyManager()


def bind_hotkeys():
    errors = hotkeys.apply({
        cfg.get("hotkey_capture", ""): lambda: pipeline.requestCapture.emit(),
        cfg.get("hotkey_fullscreen", ""): lambda: pipeline.requestFullCapture.emit(),
    })
    if errors:
        tray.showMessage("屏幕翻译", f"部分热键注册失败:\n" + "\n".join(errors),
                         QSystemTrayIcon.Warning, 3000)


bind_hotkeys()

win = MainWindow(cfg, translator)


def on_setting(key, value):
    if key in ("hotkey_capture", "hotkey_fullscreen"):
        bind_hotkeys()
    elif key == "theme":
        theme.apply(app, cfg)
    elif key == "autostart":
        set_autostart(bool(value))
        win.set_autostart_checked(bool(value))
    elif key in ("engine", "local.auto_load", "local.model_path"):
        if cfg.get("engine") == "local" and cfg.get("local.auto_load") and cfg.get("local.model_path"):
            if not translator.local_ready() and not translator.local_loading():
                translator.load_local_async()
    if key == "history_limit":
        win.refresh_history()


win.settingsChanged.connect(on_setting)

tray = QSystemTrayIcon(icon)
tray_menu = QMenu()
act_show = tray_menu.addAction("打开设置")
act_capture = tray_menu.addAction("截图翻译")
act_full = tray_menu.addAction("全屏翻译")
tray_menu.addSeparator()
act_quit = tray_menu.addAction("退出")
tray.setContextMenu(tray_menu)

act_show.triggered.connect(lambda: (win.show(), win.activateWindow()))
act_capture.triggered.connect(lambda: pipeline.requestCapture.emit())
act_full.triggered.connect(lambda: pipeline.requestFullCapture.emit())
act_quit.triggered.connect(lambda: (pipeline.shutdown(), hotkeys.unregister_all(),
                                     translator.unload_local(), tray.hide(), app.quit()))
tray.activated.connect(lambda reason: (win.show(), win.activateWindow()) if reason == QSystemTrayIcon.DoubleClick else None)

tray.show()

if cfg.get("first_run", True):
    cfg.set("first_run", False, save=True)
    hk = cfg.get("hotkey_capture", "Ctrl+Alt+S")
    tray.showMessage("屏幕翻译已启动",
                     f"已最小化到系统托盘\n快捷键 {hk.upper()} 呼出截图翻译",
                     QSystemTrayIcon.Information, 4000)

if cfg.get("local.auto_load") and cfg.get("local.model_path") and cfg.get("engine") == "local":
    translator.load_local_async()

win.show()
sys.exit(app.exec())
