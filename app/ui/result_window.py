from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui import theme

_STATUS_COLORS = {
    "idle": "fg_dim",
    "busy": "warn",
    "ok": "ok",
    "err": "danger",
}


class ResultWindow(QWidget):
    closedByUser = Signal()
    retryClicked = Signal()
    liveToggled = Signal(bool)

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._pal = theme.resolve(cfg)
        flags = Qt.FramelessWindowHint | Qt.Tool
        if cfg.get("display.always_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("翻译结果")
        self._drag_pos = None
        self._silent = False
        self._build_ui()

    def _build_ui(self):
        cfg = self._cfg
        panel = QWidget(self)
        panel.setObjectName("resultPanel")
        root = QVBoxLayout(panel)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        self.dot = QLabel()
        self.dot.setFixedSize(9, 9)
        self.dot.setStyleSheet("border-radius:4px;")
        self.status = QLabel("就绪")
        self.status.setStyleSheet("font-size:12px;")
        header.addWidget(self.dot)
        header.addWidget(self.status)
        header.addStretch(1)
        self.live_btn = QPushButton("实时: 开")
        self.live_btn.setCheckable(True)
        self.copy_btn = QPushButton("复制")
        self.retry_btn = QPushButton("重新翻译")
        close_btn = QPushButton("关闭")
        for b in (self.live_btn, self.copy_btn, self.retry_btn):
            header.addWidget(b)
        header.addWidget(close_btn)
        root.addLayout(header)

        font = QFont(self.font())
        font.setPointSize(max(9, int(cfg.get("display.font_size", 14))))
        self.body = QLabel("正在识别…")
        self.body.setObjectName("resultText")
        self.body.setFont(font)
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        root.addWidget(self.body, 1)

        width = int(cfg.get("display.wrap_width", 560))
        self.setFixedWidth(min(max(width, 300), 1200))

        src_row = QHBoxLayout()
        src_row.setSpacing(8)
        self.src_toggle = QPushButton("原文")
        self.src_toggle.setCheckable(True)
        self.src_toggle.setChecked(bool(cfg.get("display.show_source", False)))
        src_row.addWidget(self.src_toggle)
        src_row.addStretch(1)
        root.addLayout(src_row)

        self.source = QLabel("")
        self.source.setWordWrap(True)
        self.source.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.source.setVisible(self.src_toggle.isChecked())
        root.addWidget(self.source)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(panel)

        self.live_btn.toggled.connect(self._on_live_toggled)
        self.copy_btn.clicked.connect(self._copy_result)
        self.retry_btn.clicked.connect(self.retryClicked.emit)
        self.src_toggle.toggled.connect(self.source.setVisible)
        close_btn.clicked.connect(self.close)

        self._apply_status("idle", "就绪")
        self._update_dot()

    def _on_live_toggled(self, on):
        self.live_btn.setText("实时: 开" if on else "实时: 关")
        self.liveToggled.emit(on)

    def _copy_result(self):
        QApplication.clipboard().setText(self.body.text())

    def _apply_status(self, kind, text):
        key = _STATUS_COLORS.get(kind, "fg_dim")
        color = self._pal.get(key, "#888888")
        self.dot.setStyleSheet(f"background:{color};border-radius:4px;")
        self.status.setText(text)

    def _update_dot(self):
        pass

    def set_status(self, kind, text):
        try:
            self._apply_status(kind, text)
        except RuntimeError:
            pass

    def set_result(self, source, translated):
        self.body.setText(translated or "(空)")
        self.source.setText(source or "")
        self.refit()

    def set_live(self, on):
        self.live_btn.blockSignals(True)
        self.live_btn.setChecked(bool(on))
        self.live_btn.setText("实时: 开" if on else "实时: 关")
        self.live_btn.blockSignals(False)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setBrush(QColor(self._pal["panel"]))
        pen = QPen(QColor(self._pal["accent"]), 1)
        pen.setColor(QColor(120, 120, 120, 90))
        p.setPen(pen)
        p.drawRoundedRect(r, 12, 12)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def place_for_region(self, region_phys, screen):
        try:
            dpr = float(screen.devicePixelRatio() or 1.0)
        except Exception:
            dpr = 1.0
        gx = region_phys.x() / dpr
        gy = region_phys.y() / dpr
        lw = region_phys.width() / dpr
        lh = region_phys.height() / dpr
        avail = screen.availableGeometry()
        est_h = min(240, avail.height() // 2)
        w = self.width()
        x = int(gx)
        x = max(avail.left() + 8, min(x, avail.right() - w - 8))
        y = int(gy + lh + 14)
        if y + est_h > avail.bottom():
            y = int(gy - est_h - 14)
        y = max(avail.top() + 8, min(y, avail.bottom() - est_h))
        self.move(x, y)

    def refit(self):
        super().adjustSize()
        h = max(150, min(self.sizeHint().height(), 600))
        self.resize(self.width(), h)

    def shutdown(self):
        self._silent = True
        self.close()

    def closeEvent(self, e):
        if not self._silent:
            self.closedByUser.emit()
        e.accept()
