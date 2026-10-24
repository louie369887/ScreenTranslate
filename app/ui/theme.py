LIGHT = {
    "name": "light",
    "bg": "#f3f4f8",
    "panel": "#ffffff",
    "fg": "#1f2329",
    "fg_dim": "#6b7280",
    "border": "#e3e6ee",
    "field": "#ffffff",
    "btn": "#edeff5",
    "btn_hover": "#e3e6f0",
    "accent": "#2f6bff",
    "accent_soft": "#e9f0ff",
    "danger": "#ef4444",
    "ok": "#16a34a",
    "warn": "#d97706",
    "panel_rgba": "rgba(255,255,255,240)",
    "border_soft": "rgba(31,35,41,0.10)",
}

DARK = {
    "name": "dark",
    "bg": "#141519",
    "panel": "#1e2026",
    "fg": "#e7e9ee",
    "fg_dim": "#9aa0ab",
    "border": "#30333c",
    "field": "#262932",
    "btn": "#2b2e37",
    "btn_hover": "#353945",
    "accent": "#4f8cff",
    "accent_soft": "#20304d",
    "danger": "#f87171",
    "ok": "#34d399",
    "warn": "#fbbf24",
    "panel_rgba": "rgba(30,32,38,242)",
    "border_soft": "rgba(231,233,238,0.12)",
}

QSS_TEMPLATE = """
*{outline:none;}
QWidget{background:%(bg)s;color:%(fg)s;font-size:13px;}
QMainWindow{background:%(bg)s;}
QStatusBar{background:%(panel)s;border-top:1px solid %(border)s;color:%(fg_dim)s;}
QToolTip{background:%(panel)s;color:%(fg)s;border:1px solid %(border)s;padding:4px 8px;border-radius:4px;}

QPushButton{background:%(btn)s;border:1px solid %(border)s;border-radius:6px;padding:5px 14px;}
QPushButton:hover{background:%(btn_hover)s;}
QPushButton:pressed{background:%(accent_soft)s;}
QPushButton:disabled{color:%(fg_dim)s;background:%(btn)s;}
QPushButton#accentBtn{background:%(accent)s;color:#ffffff;border-color:%(accent)s;font-weight:bold;}
QPushButton#accentBtn:hover{background:%(accent)s;}
QPushButton#dangerBtn{background:transparent;color:%(danger)s;border-color:%(border)s;}

QLineEdit,QTextEdit,QPlainTextEdit,QSpinBox,QDoubleSpinBox,QComboBox{
background:%(field)s;border:1px solid %(border)s;border-radius:6px;padding:4px 8px;
selection-background-color:%(accent)s;selection-color:#ffffff;}
QLineEdit:focus,QTextEdit:focus,QPlainTextEdit:focus,QSpinBox:focus,QDoubleSpinBox:focus,QComboBox:focus{border-color:%(accent)s;}
QComboBox::drop-down{border:none;width:20px;}
QComboBox QAbstractItemView{background:%(panel)s;border:1px solid %(border)s;selection-background-color:%(accent_soft);selection-color:%(fg)s;}

QCheckBox{spacing:8px;}
QCheckBox::indicator{width:16px;height:16px;border:1px solid %(border)s;border-radius:4px;background:%(field)s;}
QCheckBox::indicator:hover{border-color:%(accent)s;}
QCheckBox::indicator:checked{background:%(accent)s;border-color:%(accent)s;}

QListWidget,QTableWidget,QTreeWidget{background:%(field)s;border:1px solid %(border)s;border-radius:6px;}
QListWidget::item{padding:6px 8px;border-radius:4px;}
QListWidget::item:selected{background:%(accent_soft)s;color:%(fg)s;}
QListWidget::item:hover{background:%(btn)s;}

QGroupBox{border:1px solid %(border)s;border-radius:8px;margin-top:12px;padding-top:6px;font-weight:bold;}
QGroupBox::title{subcontrol-origin:margin;left:12px;top:2px;padding:0 4px;color:%(fg_dim)s;}

QSlider::groove:horizontal{height:4px;background:%(btn)s;border-radius:2px;}
QSlider::sub-page:horizontal{background:%(accent)s;border-radius:2px;}
QSlider::handle:horizontal{width:14px;height:14px;margin:-5px 0;border-radius:7px;background:%(accent)s;}
QSlider::handle:horizontal:hover{background:%(accent)s;}

QScrollBar:vertical{background:transparent;width:9px;margin:2px;}
QScrollBar::handle:vertical{background:%(border)s;border-radius:4px;min-height:30px;}
QScrollBar::handle:vertical:hover{background:%(fg_dim)s;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
QScrollBar:horizontal{background:transparent;height:9px;margin:2px;}
QScrollBar::handle:horizontal{background:%(border)s;border-radius:4px;min-width:30px;}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{width:0;}

QMenu{background:%(panel)s;border:1px solid %(border)s;border-radius:8px;padding:4px;}
QMenu::item{padding:6px 24px;border-radius:4px;}
QMenu::item:selected{background:%(accent_soft)s;}
QMenu::separator{height:1px;background:%(border)s;margin:4px 8px;}

QLabel{background:transparent;}
QLabel[dim=\"true\"]{color:%(fg_dim)s;}
QLabel[h1=\"true\"]{font-size:17px;font-weight:bold;}
QLabel[link=\"true\"]{color:%(accent)s;}

QWidget#sidebar{background:%(panel)s;border-right:1px solid %(border)s;}
QPushButton[nav=\"true\"]{text-align:left;border:none;background:transparent;padding:9px 16px;border-radius:8px;font-size:13px;color:%(fg)s;}
QPushButton[nav=\"true\"]:hover{background:%(btn)s;}
QPushButton[nav=\"true\"]:checked{background:%(accent_soft)s;color:%(accent)s;font-weight:bold;}

QWidget#headerBar{background:%(panel)s;border-bottom:1px solid %(border)s;}
QWidget#pagePanel{background:%(panel)s;border-radius:10px;border:1px solid %(border)s;}

QWidget#overlayBar{background:rgba(17,19,24,215);border-radius:10px;}
QWidget#overlayBar QLabel{color:#d6dae2;background:transparent;font-size:12px;}
QWidget#overlayBar QPushButton{background:rgba(255,255,255,0.08);color:#e8eaf0;border:none;border-radius:6px;padding:5px 12px;font-size:13px;}
QWidget#overlayBar QPushButton:hover{background:rgba(255,255,255,0.16);}
QWidget#overlayBar QPushButton:checked{background:%(accent)s;color:#ffffff;}
QWidget#overlayBar QPushButton#goBtn{background:%(accent)s;color:#ffffff;font-weight:bold;padding:5px 22px;}
QWidget#overlayBar QPushButton#goBtn:hover{background:%(accent)s;}

QLabel#sizeTag{background:rgba(17,19,24,225);color:#ffffff;border-radius:4px;padding:2px 8px;font-size:12px;}
QLabel#hintText{color:rgba(255,255,255,235);font-size:15px;background:transparent;}

QWidget#resultPanel QPushButton{background:rgba(127,127,127,0.18);border:none;border-radius:6px;padding:4px 12px;font-size:12px;color:%(fg)s;}
QWidget#resultPanel QPushButton:hover{background:rgba(127,127,127,0.32);}
QWidget#resultPanel QPushButton:checked{background:%(accent)s;color:#ffffff;}
"""


def resolve(cfg):
    mode = cfg.get("theme", "system")
    if mode == "light":
        return dict(LIGHT)
    if mode == "dark":
        return dict(DARK)
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            lum = app.palette().window().color().lightness()
            return dict(DARK if lum < 128 else LIGHT)
    except Exception:
        pass
    return dict(LIGHT)


def apply(app, cfg):
    pal = resolve(cfg)
    try:
        app.setStyleSheet(QSS_TEMPLATE % pal)
    except Exception:
        pass
