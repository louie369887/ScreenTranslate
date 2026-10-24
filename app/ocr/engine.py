import re
import statistics
import threading

import numpy as np

_CJK = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
_PUNCT_END = tuple(".,;:!?\u3001\u3002\uff0c\uff1b\uff1a\uff01\uff1f…)]}\u201d\"'")


def _join(a, b):
    if not a:
        return b
    if not b:
        return a
    if _CJK.search(a[-1]) and _CJK.search(b[0]):
        return a + b
    return a + " " + b


def _prepare(img, scale_cfg):
    h, w = img.shape[:2]
    scale = 1.0
    if scale_cfg == "auto":
        scale = 2.0 if max(h, w) < 1000 else 1.0
    else:
        try:
            scale = float(scale_cfg)
        except (TypeError, ValueError):
            scale = 1.0
    if scale and abs(scale - 1.0) > 0.01:
        from PIL import Image
        im = Image.fromarray(img[:, :, ::-1])
        im = im.resize((max(8, int(w * scale)), max(8, int(h * scale))), Image.LANCZOS)
        return np.asarray(im)[:, :, ::-1].copy()
    return img


class OcrEngine:
    def __init__(self, cfg):
        self.cfg = cfg
        self._eng = None
        self._lock = threading.Lock()

    def _ensure(self):
        if self._eng is None:
            from rapidocr_onnxruntime import RapidOCR
            self._eng = RapidOCR()
        return self._eng

    def recognize(self, img_bgr):
        with self._lock:
            eng = self._ensure()
            img = _prepare(img_bgr, self.cfg.get("ocr.scale", "auto"))
            try:
                result, _elapse = eng(img)
            except Exception as e:
                raise RuntimeError(f"OCR 引擎错误: {e}")
        records = []
        min_score = float(self.cfg.get("ocr.min_score", 0.5))
        for item in result or []:
            try:
                box, text, score = item[0], item[1], float(item[2])
            except Exception:
                continue
            text = (text or "").strip()
            if not text or score < min_score:
                continue
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)
            records.append({
                "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2, "h": max(1.0, y1 - y0),
                "text": text,
            })
        return self._layout(records), len(records)

    def _layout(self, records):
        if not records:
            return ""
        avg_h = statistics.median(r["h"] for r in records)
        records.sort(key=lambda r: r["cy"])
        lines = []
        prev = None
        for rec in records:
            if prev is None or (rec["cy"] - prev["cy"]) > max(prev["h"], avg_h) * 0.85:
                lines.append([rec])
            else:
                lines[-1].append(rec)
            prev = rec
        line_objs = []
        for ln in lines:
            ln.sort(key=lambda r: r["cx"])
            text = ""
            for rec in ln:
                text = _join(text, rec["text"])
            cy = sum(r["cy"] for r in ln) / len(ln)
            bottom = max(r["y1"] for r in ln)
            line_objs.append({"text": text, "cy": cy, "bottom": bottom})
        merge = bool(self.cfg.get("ocr.merge_paragraph", True))
        paragraphs = []
        cur = ""
        prev_line = None
        gap_limit = avg_h * 2.2
        for lo in line_objs:
            if cur and merge and prev_line is not None:
                vertical_gap = lo["cy"] - prev_line["bottom"]
                same_para = vertical_gap < gap_limit and not cur.endswith(_PUNCT_END)
            else:
                same_para = False
            if same_para:
                cur = _join(cur, lo["text"])
            else:
                if cur:
                    paragraphs.append(cur)
                cur = lo["text"]
            prev_line = lo
        if cur:
            paragraphs.append(cur)
        return "\n".join(paragraphs)
