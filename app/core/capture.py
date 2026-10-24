import ctypes

import mss
import numpy as np
from PIL import Image

user32 = ctypes.windll.user32

_VX, _VY, _VW, _VH = 76, 77, 78, 79


def clamp_region(left, top, width, height):
    sx = user32.GetSystemMetrics(_VX)
    sy = user32.GetSystemMetrics(_VY)
    sw = user32.GetSystemMetrics(_VW)
    sh = user32.GetSystemMetrics(_VH)
    l = max(int(left), sx)
    t = max(int(top), sy)
    r = min(int(left + width), sx + sw)
    b = min(int(top + height), sy + sh)
    if r <= l or b <= t:
        return int(left), int(top), int(width), int(height)
    return l, t, r - l, b - t


def grab_region(left, top, width, height):
    left, top, width, height = clamp_region(left, top, width, height)
    if width <= 0 or height <= 0:
        raise ValueError("无效的截屏区域")
    with mss.mss() as sct:
        raw = np.asarray(sct.grab({"left": int(left), "top": int(top), "width": int(width), "height": int(height)}))
    return raw[:, :, :3].copy()


def _thumb_gray(img, h=96):
    im = Image.fromarray(img[:, :, ::-1]).convert("L")
    w = max(8, int(im.width * h / max(1, im.height)))
    im = im.resize((w, h))
    return np.asarray(im, dtype=np.float32)


def diff_ratio(a, b):
    if a is None or b is None:
        return 255.0
    ta = _thumb_gray(a)
    tb = _thumb_gray(b)
    if ta.shape != tb.shape:
        return 255.0
    return float(np.abs(ta - tb).mean())
