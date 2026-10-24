from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap


def app_pixmap(size=256):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    r = size * 0.22
    path.addRoundedRect(QRectF(0, 0, size, size), r, r)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor("#4f8cff"))
    grad.setColorAt(1.0, QColor("#2456e0"))
    p.fillPath(path, grad)
    f = QFont("Microsoft YaHei UI", int(size * 0.52))
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#ffffff"))
    rect = QRectF(0, -size * 0.04, size, size)
    p.drawText(rect, Qt.AlignCenter, "译")
    p.end()
    return pm


def app_icon():
    return QIcon(app_pixmap(256))
