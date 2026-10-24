from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core import win_tools
from app.ui import theme

MODE_AREA = "area"
MODE_WINDOW = "window"
MODE_FULL = "full"

_TIPS = {
    MODE_AREA: "拖拽框选区域，单击可直接选中窗口",
    MODE_WINDOW: "移动鼠标选择窗口，单击确认",
    MODE_FULL: "将翻译整个屏幕",
}


class CaptureOverlay(QWidget):
    selected = Signal(object)
    cancelled = Signal()

    def __init__(self, cfg, screen, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setCursor(Qt.CrossCursor)
        self._cfg = cfg
        self._pal = theme.resolve(cfg)
        self._screen = screen
        self._geo = screen.geometry()
        try:
            self._dpr = float(screen.devicePixelRatio() or 1.0)
        except Exception:
            self._dpr = 1.0
        self._shot = screen.grabWindow(0)
        self._mode = cfg.get("capture.default_mode", MODE_AREA)
        if self._mode not in _TIPS:
            self._mode = MODE_AREA
        self._sel = None
        self._origin = None
        self._hover = None
        self._confirmed = False
        self._pending_win_click = None

        self.setWindowTitle("屏幕翻译")
        self.setGeometry(self._geo)
        self._build_bar()
        self._build_hint()
        self._update_tip()

    def _build_bar(self):
        bar = QWidget(self)
        bar.setObjectName("overlayBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(4)
        self._group = QButtonGroup(bar)
        self._group.setExclusive(True)
        self._btn_area = QPushButton("区域")
        self._btn_win = QPushButton("窗口")
        self._btn_full = QPushButton("全屏")
        for i, b in enumerate((self._btn_area, self._btn_win, self._btn_full)):
            b.setCheckable(True)
            self._group.addButton(b, i)
            lay.addWidget(b)
        self._btn_area.setChecked(self._mode == MODE_AREA)
        self._btn_win.setChecked(self._mode == MODE_WINDOW)
        self._btn_full.setChecked(self._mode == MODE_FULL)
        self._tip = QLabel("")
        lay.addSpacing(8)
        lay.addWidget(self._tip)
        lay.addStretch(1)
        go = QPushButton("翻 译")
        go.setObjectName("goBtn")
        cancel = QPushButton("取消")
        lay.addWidget(go)
        lay.addWidget(cancel)
        go.clicked.connect(self.confirm)
        cancel.clicked.connect(self.cancel)
        self._group.idClicked.connect(self._on_mode)
        bar.adjustSize()
        self._bar = bar

    def _build_hint(self):
        self._size_tag = QLabel("", self)
        self._size_tag.setObjectName("sizeTag")
        self._size_tag.hide()

    def _place_children(self):
        w, h = self.width(), self.height()
        bw = self._bar.width()
        self._bar.move(max(8, (w - bw) // 2), 14)
        self._size_tag.adjustSize()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place_children()

    def showEvent(self, e):
        super().showEvent(e)
        self.raise_()
        self.activateWindow()
        self.setFocus()
        self._place_children()

    def _on_mode(self, bid):
        self._mode = {0: MODE_AREA, 1: MODE_WINDOW, 2: MODE_FULL}[bid]
        self._origin = None
        if self._mode == MODE_FULL:
            self._sel = QRect(0, 0, self.width(), self.height())
        else:
            self._sel = None
            self._hover = None
        self._update_tip()
        self.update()

    def _update_tip(self):
        self._tip.setText(_TIPS[self._mode])

    def _to_physical(self, rc):
        g = self._geo
        d = self._dpr
        x0 = round((g.x() + rc.x()) * d)
        y0 = round((g.y() + rc.y()) * d)
        x1 = round((g.x() + rc.right() + 1) * d)
        y1 = round((g.y() + rc.bottom() + 1) * d)
        return QRect(x0, y0, max(1, x1 - x0), max(1, y1 - y0))

    def _local_from_physical(self, px, py):
        g = self._geo
        d = self._dpr
        return px / d - g.x(), py / d - g.y()

    def _window_at_local(self, pos):
        px, py = (self._geo.x() + pos.x()), (self._geo.y() + pos.y())
        ppx = round(px * self._dpr)
        ppy = round(py * self._dpr)
        info = win_tools.window_at(ppx, ppy, exclude={int(self.winId())})
        if not info:
            return None
        lx, ly = self._local_from_physical(info["x"], info["y"])
        lw = max(4, round(info["w"] / self._dpr))
        lh = max(4, round(info["h"] / self._dpr))
        return {"rect": QRect(round(lx), round(ly), lw, lh), "title": info["title"]}

    def _effective_rect(self):
        if self._mode == MODE_FULL:
            return self._sel
        if self._mode == MODE_WINDOW:
            return self._hover["rect"] if self._hover else None
        return self._sel

    def paintEvent(self, e):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self._shot)
        r = self._effective_rect()
        W, H = self.width(), self.height()
        dim = QColor(0, 0, 0, 110)
        if r is None or r.width() <= 0 or r.height() <= 0:
            p.fillRect(0, 0, W, H, dim)
            p.setPen(QPen(QColor(255, 255, 255, 200)))
            f = QFont(self.font())
            f.setPointSize(13)
            p.setFont(f)
            p.drawText(QRect(0, H // 2 - 40, W, 80), Qt.AlignCenter,
                       "拖拽框选要翻译的区域\n单击可选中整个窗口")
        else:
            top = max(0, r.top())
            bottom = min(H, r.bottom() + 1)
            left = max(0, r.left())
            right = min(W, r.right() + 1)
            p.fillRect(0, 0, W, top, dim)
            p.fillRect(0, bottom, W, H - bottom, dim)
            p.fillRect(0, top, left, bottom - top, dim)
            p.fillRect(right, top, W - right, bottom - top, dim)
            accent = QColor(self._pal["accent"])
            pen = QPen(accent, 2)
            if self._mode == MODE_WINDOW and self._sel is None and not self._origin:
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.drawRect(r)
            hs = 7
            p.setBrush(accent)
            for cx, cy in ((r.left(), r.top()), (r.right(), r.top()),
                           (r.left(), r.bottom()), (r.right(), r.bottom())):
                p.drawRect(cx - hs // 2, cy - hs // 2, hs, hs)
            p.setBrush(Qt.NoBrush)
            if self._mode == MODE_WINDOW and self._hover:
                title = self._hover.get("title") or ""
                if title:
                    fm = p.fontMetrics()
                    text = fm.elidedText(title, Qt.ElideMiddle, 320)
                    tw = fm.horizontalAdvance(text) + 16
                    th = fm.height() + 8
                    tx = r.left()
                    ty = r.top() - th - 6
                    if ty < 2:
                        ty = r.top() + 6
                    p.setPen(Qt.NoPen)
                    p.setBrush(QColor(17, 19, 24, 225))
                    p.drawRoundedRect(tx, ty, tw, th, 4, 4)
                    p.setPen(QColor("#ffffff"))
                    p.drawText(tx + 8, ty, tw - 16, th, Qt.AlignVCenter, text)

    def _update_size_tag(self, r):
        if r is None or r.width() <= 0:
            self._size_tag.hide()
            return
        self._size_tag.setText(f"{r.width()} × {r.height()}")
        self._size_tag.adjustSize()
        tx = r.right() - self._size_tag.width()
        ty = r.bottom() + 8
        if ty + self._size_tag.height() > self.height() - 4:
            ty = r.top() - self._size_tag.height() - 8
        tx = max(4, min(tx, self.width() - self._size_tag.width() - 4))
        ty = max(4, ty)
        self._size_tag.move(tx, ty)
        self._size_tag.show()

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.cancel()
            return
        if e.button() != Qt.LeftButton:
            return
        pos = e.pos()
        if self._mode == MODE_AREA:
            hit = self._window_at_local(pos)
            self._origin = pos
            self._sel = None
            self._pending_win_click = hit
            self.update()
        elif self._mode == MODE_WINDOW:
            hit = self._window_at_local(pos)
            if hit:
                self._sel = hit["rect"]
                self.update()
        else:
            self._sel = QRect(0, 0, self.width(), self.height())
            self.update()

    def mouseMoveEvent(self, e):
        pos = e.pos()
        changed = False
        if self._origin is not None and self._mode == MODE_AREA:
            self._sel = QRect(self._origin, pos).normalized()
            changed = True
        elif self._mode == MODE_WINDOW and self._origin is None:
            hit = self._window_at_local(pos)
            if hit != self._hover:
                self._hover = hit
                changed = True
        if changed or True:
            self.update()
            self._update_size_tag(self._effective_rect())

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        if self._mode == MODE_AREA and self._origin is not None:
            moved = self._sel is not None and self._sel.width() > 8 and self._sel.height() > 8
            self._origin = None
            if not moved:
                hit = getattr(self, "_pending_win_click", None)
                if hit:
                    self._sel = hit["rect"]
                elif self._sel is None:
                    self._sel = QRect(e.pos().x() - 60, e.pos().y() - 30, 120, 60)
                self._pending_win_click = None
            if self._sel is not None:
                self._sel = self._sel.intersected(QRect(0, 0, self.width(), self.height()))
            self.update()
            self._update_size_tag(self._effective_rect())

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.confirm()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cancel()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.confirm()

    def confirm(self):
        r = self._effective_rect()
        if r is None or r.width() < 4 or r.height() < 4:
            self._tip.setText("请先选择区域或窗口，再点击翻译")
            return
        self._confirmed = True
        phys = self._to_physical(r)
        self.selected.emit(phys)
        self.close()

    def cancel(self):
        self.close()

    def closeEvent(self, e):
        if not self._confirmed:
            self.cancelled.emit()
        e.accept()
        self.deleteLater()
