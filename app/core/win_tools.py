import ctypes
import os
import sys
from ctypes import wintypes

import winreg

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def ensure_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def cursor_pos():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return int(pt.x), int(pt.y)


def _rect_of(hwnd):
    rect = wintypes.RECT()
    hr = dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect))
    if hr != 0 or (rect.right - rect.left) <= 0:
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None
    return int(rect.left), int(rect.top), int(w), int(h)


def _cloaked(hwnd):
    val = ctypes.c_uint(0)
    dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(val), ctypes.sizeof(val))
    return val.value != 0


def list_windows():
    result = []

    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.IsIconic(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        ex = user32.GetWindowLongW(hwnd, -20)
        if ex & 0x00000080:
            return True
        if _cloaked(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, cls, 64)
        if cls.value in ("Shell_TrayWnd", "Progman", "WorkerW", "SysListView32", "Shell_SecondaryTrayWnd"):
            return True
        r = _rect_of(hwnd)
        if not r:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        x, y, w, h = r
        result.append({"hwnd": int(hwnd), "title": buf.value, "x": x, "y": y, "w": w, "h": h})
        return True

    proc = WNDENUMPROC(cb)
    user32.EnumWindows(proc, 0)
    return result


def window_at(px, py, exclude=()):
    for info in list_windows():
        if info["hwnd"] in exclude:
            continue
        if info["x"] <= px < info["x"] + info["w"] and info["y"] <= py < info["y"] + info["h"]:
            return info
    return None


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "ScreenTranslator"


def _autostart_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'


def get_autostart():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, VALUE_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled):
    try:
        if enabled:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, VALUE_NAME, 0, winreg.REG_SZ, _autostart_command())
        else:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                try:
                    winreg.DeleteValue(k, VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False
