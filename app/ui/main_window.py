import os
import threading
import time
from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSlider, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)
from app.config import TARGET_LANGS
from app.translate import openai_api
from app.ui import theme
from app.ui.history_widget import HistoryWidget
from app.ui.icons import app_pixmap


class HotkeyEdit(QLineEdit):
    hotkeyChanged = Signal(str)
    def __init__(self, value="", parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self._value = (value or "").strip().lower()
        self._update_display()
        self.setMinimumWidth(180)
        self.setPlaceholderText("点击后按下组合键")
    def _update_display(self):
        if not self._value:
            self.setText("")
            return
        parts = [p.capitalize() for p in self._value.split("+")]
        self.setText(" + ".join(parts).replace("Windows", "Win"))
    def value(self):
        return self._value
    def setValue(self, v):
        self._value = (v or "").strip().lower()
        self._update_display()
    def keyPressEvent(self, e):
        key = e.key()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_CapsLock, Qt.Key_NumLock):
            return
        if key == Qt.Key_Escape:
            self._value = ""
            self._update_display()
            self.hotkeyChanged.emit("")
            self.clearFocus()
            return
        mods = int(e.modifiers())
        seq = QKeySequence(mods | key)
        s = seq.toString(QKeySequence.PortableText)
        parts = []
        for p in s.split("+"):
            pl = p.lower()
            if pl == "meta":
                pl = "windows"
            parts.append(pl)
        norm = "+".join(parts)
        self._value = norm
        self._update_display()
        self.hotkeyChanged.emit(norm)
        self.clearFocus()


class MainWindow(QMainWindow):
    settingsChanged = Signal(str, object)
    def __init__(self, cfg, translator, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.translator = translator
        self.setWindowTitle("屏幕翻译 - 设置")
        self.setMinimumSize(860, 580)
        self.resize(940, 640)
        self.setWindowIcon(QApplication.windowIcon())
        self._api_syncing = False
        self._build_ui()
        self._load_values()
        self._connect_signals()
        self._apply_engine_status()
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self._build_header())
        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        root.addWidget(right, 1)
        pages = [
            ("常规", self._page_general()),
            ("快捷键", self._page_hotkeys()),
            ("翻译服务", self._page_service()),
            ("OCR 识别", self._page_ocr()),
            ("实时翻译", self._page_realtime()),
            ("显示", self._page_display()),
            ("历史记录", self._page_history()),
            ("关于", self._page_about()),
        ]
        for _title, widget in pages:
            sw = QScrollArea()
            sw.setWidgetResizable(True)
            sw.setFrameShape(QFrame.NoFrame)
            sw.setWidget(widget)
            self.stack.addWidget(sw)
        self.statusBar().showMessage("就绪")
        self.engine_status = QLabel("")
        self.statusBar().addPermanentWidget(self.engine_status)
    def _build_sidebar(self):
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(170)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(12, 16, 12, 12)
        lay.setSpacing(6)
        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)
        il = QLabel()
        il.setPixmap(app_pixmap(36))
        logo_row.addWidget(il)
        lbl = QLabel("屏幕翻译")
        lbl.setStyleSheet("font-weight:bold;font-size:15px;")
        logo_row.addWidget(lbl)
        logo_row.addStretch(1)
        lay.addLayout(logo_row)
        lay.addSpacing(8)
        titles = ["常规", "快捷键", "翻译服务", "OCR 识别", "实时翻译", "显示", "历史记录", "关于"]
        self._nav_btns = []
        for i, title in enumerate(titles):
            b = QPushButton(title)
            b.setProperty("nav", True)
            b.setCheckable(True)
            lay.addWidget(b)
            self._nav_btns.append(b)
            b.clicked.connect(lambda _, idx=i: self._nav_to(idx))
        lay.addStretch()
        ver = QLabel("v1.0.0  Hy-MT2")
        ver.setStyleSheet("color:#999;font-size:11px;")
        lay.addWidget(ver)
        self._nav_to(0)
        return side
    def _build_header(self):
        bar = QWidget()
        bar.setObjectName("headerBar")
        bar.setFixedHeight(48)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 20, 0)
        self.header_title = QLabel("常规设置")
        self.header_title.setStyleSheet("font-size:15px;font-weight:bold;")
        lay.addWidget(self.header_title)
        lay.addStretch()
        return bar
    def _nav_to(self, idx):
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self._nav_btns):
            b.setChecked(i == idx)
        names = ["常规设置", "快捷键设置", "翻译服务设置", "OCR 识别设置", "实时翻译设置", "显示设置", "翻译历史记录", "关于"]
        self.header_title.setText(names[idx] if idx < len(names) else "")
    def _vbox_page(self, margin=24):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(margin, margin, margin, margin)
        lay.setSpacing(12)
        return w, lay
    def _form_row(self, lay, label_text, widget, tip=""):
        row = QHBoxLayout()
        row.setSpacing(12)
        lbl = QLabel(label_text)
        lbl.setFixedWidth(130)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(lbl)
        row.addWidget(widget)
        if tip:
            t = QLabel(tip)
            t.setStyleSheet("color:#888;font-size:11px;")
            t.setMaximumWidth(240)
            t.setWordWrap(True)
            row.addWidget(t)
        else:
            row.addStretch(1)
        lay.addLayout(row)
    def _set(self, key, value):
        self.cfg.set(key, value)
        self.settingsChanged.emit(key, value)
    def _page_general(self):
        w, lay = self._vbox_page()
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["跟随系统", "浅色", "深色"])
        self._form_row(lay, "主题", self.combo_theme)
        self.combo_lang = QComboBox()
        self.combo_lang.setEditable(True)
        self.combo_lang.addItems(TARGET_LANGS)
        self._form_row(lay, "目标语言", self.combo_lang, "翻译的目标语种")
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["区域", "窗口", "全屏"])
        self._form_row(lay, "默认框选模式", self.combo_mode)
        self.chk_tray = QCheckBox("关闭主窗口时最小化到系统托盘")
        self._form_row(lay, "窗口行为", self.chk_tray)
        self.chk_autostart = QCheckBox("开机自动启动")
        self._form_row(lay, "自启动", self.chk_autostart)
        lay.addStretch(1)
        return w
    def _page_hotkeys(self):
        w, lay = self._vbox_page()
        self.he_capture = HotkeyEdit(self.cfg.get("hotkey_capture", ""))
        self._form_row(lay, "截图翻译", self.he_capture, "框选区域或选中窗口后实时翻译")
        self.he_fullscreen = HotkeyEdit(self.cfg.get("hotkey_fullscreen", ""))
        self._form_row(lay, "全屏翻译", self.he_fullscreen, "直接对当前屏幕实时翻译")
        note = QLabel("提示: 点击输入框后直接按下键盘组合键，按 Esc 清除")
        note.setStyleSheet("color:#888;")
        lay.addWidget(note)
        lay.addStretch(1)
        return w
    def _page_service(self):
        w, lay = self._vbox_page()
        self.combo_engine = QComboBox()
        self.combo_engine.addItems(["本地模型 (Hy-MT2)", "API 接口"])
        self._form_row(lay, "翻译引擎", self.combo_engine)
        self.sub_stack = QStackedWidget()
        self.sub_stack.addWidget(self._sub_local_page())
        self.sub_stack.addWidget(self._sub_api_page())
        lay.addWidget(self.sub_stack, 1)
        return w

    def _sub_local_page(self):
        w, lay = self._vbox_page(margin=8)
        path_row = QHBoxLayout()
        self.edit_model_path = QLineEdit()
        self.edit_model_path.setPlaceholderText("选择 .gguf 模型文件路径")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self._browse_model)
        path_row.addWidget(self.edit_model_path)
        path_row.addWidget(btn_browse)
        lay.addLayout(path_row)
        link = QLabel()
        link.setOpenExternalLinks(True)
        link.setText('<a href="https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF" style="color:#4f8cff;">下载 Hy-MT2 GGUF</a> | <a href="https://modelscope.cn/models/Tencent-Hunyuan/Hy-MT2-1.8B-GGUF" style="color:#4f8cff;">ModelScope</a>')
        link.setStyleSheet("font-size:11px;")
        lay.addWidget(link)
        self.chk_auto_load = QCheckBox("启动时自动加载模型")
        lay.addWidget(self.chk_auto_load)
        self.spin_gpu = QSpinBox(); self.spin_gpu.setRange(0, 100)
        self.spin_gpu.setSpecialValueText("0 (仅CPU)"); self.spin_gpu.setSuffix(" 层")
        self._form_row(lay, "GPU 卸载层数", self.spin_gpu, "0=仅CPU")
        self.spin_ctx = QSpinBox(); self.spin_ctx.setRange(512, 32768)
        self.spin_ctx.setSingleStep(512); self.spin_ctx.setSuffix(" tokens")
        self._form_row(lay, "上下文长度", self.spin_ctx)
        self.spin_threads = QSpinBox(); self.spin_threads.setRange(0, 128)
        self.spin_threads.setSpecialValueText("自动")
        self._form_row(lay, "CPU 线程数", self.spin_threads)
        gl = QFormLayout(); gl.setContentsMargins(0,0,0,0); gl.setSpacing(8)
        self.dspin_temp = QDoubleSpinBox(); self.dspin_temp.setRange(0.0,2.0); self.dspin_temp.setSingleStep(0.05); self.dspin_temp.setDecimals(2)
        gl.addRow("temperature", self.dspin_temp)
        self.dspin_top_p = QDoubleSpinBox(); self.dspin_top_p.setRange(0.0,1.0); self.dspin_top_p.setSingleStep(0.01); self.dspin_top_p.setDecimals(2)
        gl.addRow("top_p", self.dspin_top_p)
        self.spin_top_k = QSpinBox(); self.spin_top_k.setRange(-1, 256)
        gl.addRow("top_k", self.spin_top_k)
        self.dspin_rep = QDoubleSpinBox(); self.dspin_rep.setRange(0.5,2.0); self.dspin_rep.setSingleStep(0.01); self.dspin_rep.setDecimals(2)
        gl.addRow("repeat_penalty", self.dspin_rep)
        self.spin_max_tok = QSpinBox(); self.spin_max_tok.setRange(128, 8192); self.spin_max_tok.setSingleStep(64)
        gl.addRow("max_tokens", self.spin_max_tok)
        grp = QGroupBox("高级推理参数"); grp.setLayout(gl)
        lay.addWidget(grp)
        self.prompt_edit = QPlainTextEdit(); self.prompt_edit.setMaximumHeight(120)
        self._form_row(lay, "翻译提示词", self.prompt_edit)
        br = QHBoxLayout()
        self.btn_load = QPushButton("加载模型"); self.btn_load.setObjectName("accentBtn")
        self.btn_unload = QPushButton("卸载模型")
        br.addWidget(self.btn_load); br.addWidget(self.btn_unload)
        lay.addLayout(br)
        self.lbl_model_status = QLabel(""); self.lbl_model_status.setStyleSheet("font-size:12px;")
        lay.addWidget(self.lbl_model_status)
        lay.addStretch(1)
        return w

    def _sub_api_page(self):
        w, lay = self._vbox_page(margin=8)
        split = QHBoxLayout()
        ll = QVBoxLayout(); ll.setSpacing(6)
        self.api_list = QListWidget(); ll.addWidget(self.api_list, 1)
        ab = QHBoxLayout()
        ba = QPushButton("+ 添加"); ba.setObjectName("accentBtn")
        bd = QPushButton("删除"); bd.setObjectName("dangerBtn")
        ab.addWidget(ba); ab.addWidget(bd)
        ll.addLayout(ab)
        split.addLayout(ll, 2)
        rl = QVBoxLayout(); rl.setSpacing(8)
        form = QFormLayout(); form.setSpacing(8)
        self.api_name = QLineEdit(); self.api_name.setPlaceholderText("接口名称")
        form.addRow("名称", self.api_name)
        self.api_url = QLineEdit(); self.api_url.setPlaceholderText("https://api.deepseek.com")
        form.addRow("Base URL", self.api_url)
        self.api_key = QLineEdit(); self.api_key.setPlaceholderText("API Key"); self.api_key.setEchoMode(QLineEdit.Password)
        form.addRow("API Key", self.api_key)
        self.api_model = QLineEdit(); self.api_model.setPlaceholderText("deepseek-chat")
        form.addRow("模型名", self.api_model)
        rl.addLayout(form)
        pr = QHBoxLayout()
        for name, url, model in [("DeepSeek","https://api.deepseek.com","deepseek-chat"),("OpenAI","https://api.openai.com","gpt-4o-mini"),("Ollama","http://localhost:11434","hy-mt2-1.8b"),("vLLM","http://localhost:8000","hy-mt2-1.8b")]:
            btn = QPushButton(name); btn.setFixedHeight(28); pr.addWidget(btn)
            btn.clicked.connect(lambda _, u=url, m=model: self._apply_preset(u, m))
        rl.addLayout(pr)
        ar = QHBoxLayout()
        self.btn_api_save = QPushButton("保存修改"); self.btn_api_activate = QPushButton("设为当前"); self.btn_api_test = QPushButton("测试连接")
        ar.addWidget(self.btn_api_save); ar.addWidget(self.btn_api_activate); ar.addWidget(self.btn_api_test)
        rl.addLayout(ar)
        self.lbl_api_test = QLabel(""); self.lbl_api_test.setWordWrap(True); self.lbl_api_test.setStyleSheet("font-size:11px;")
        rl.addWidget(self.lbl_api_test); rl.addStretch(1)
        split.addLayout(rl, 3)
        lay.addLayout(split)
        ba.clicked.connect(self._add_api); bd.clicked.connect(self._del_api)
        self.btn_api_save.clicked.connect(self._save_api); self.btn_api_activate.clicked.connect(self._activate_api); self.btn_api_test.clicked.connect(self._test_api)
        self.api_list.currentRowChanged.connect(self._on_api_selected)
        return w

    def _page_ocr(self):
        w, lay = self._vbox_page()
        lbl = QLabel("内置 RapidOCR 离线识别，支持中英文，无需联网"); lbl.setStyleSheet("color:#888;"); lay.addWidget(lbl)
        self.combo_ocr_scale = QComboBox(); self.combo_ocr_scale.addItems(["auto","1","1.5","2","3"])
        self._form_row(lay, "图像放大倍数", self.combo_ocr_scale, "auto: 画面小时自动放大2倍")
        self.chk_merge = QCheckBox("智能合并段落"); self._form_row(lay, "段落合并", self.chk_merge)
        self.dspin_min_score = QDoubleSpinBox(); self.dspin_min_score.setRange(0.1,0.95); self.dspin_min_score.setSingleStep(0.05); self.dspin_min_score.setDecimals(2)
        self._form_row(lay, "最低置信度", self.dspin_min_score, "低于此分数的结果将被过滤")
        lay.addStretch(1); return w

    def _page_realtime(self):
        w, lay = self._vbox_page()
        self.chk_realtime = QCheckBox("启用实时重翻 (画面变化后自动重新识别并翻译)"); lay.addWidget(self.chk_realtime)
        self.spin_interval = QSpinBox(); self.spin_interval.setRange(200,3000); self.spin_interval.setSingleStep(100); self.spin_interval.setSuffix(" ms")
        self._form_row(lay, "检测间隔", self.spin_interval, "每隔多久检测一次画面变化")
        self.spin_settle = QSpinBox(); self.spin_settle.setRange(300,5000); self.spin_settle.setSingleStep(100); self.spin_settle.setSuffix(" ms")
        self._form_row(lay, "稳定判定时间", self.spin_settle, "画面停止变化后多久触发翻译")
        self.dspin_diff = QDoubleSpinBox(); self.dspin_diff.setRange(1.0,80.0); self.dspin_diff.setSingleStep(0.5); self.dspin_diff.setDecimals(1)
        self._form_row(lay, "变化灵敏度", self.dspin_diff, "数值越小越灵敏")
        self.spin_max_runs = QSpinBox(); self.spin_max_runs.setRange(0,500); self.spin_max_runs.setSpecialValueText("0 = 无限")
        self._form_row(lay, "最大自动翻译次数", self.spin_max_runs, "0表示不限制")
        lay.addStretch(1); return w

    def _page_display(self):
        w, lay = self._vbox_page()
        orow = QHBoxLayout()
        self.slider_opacity = QSlider(Qt.Horizontal); self.slider_opacity.setRange(40,100)
        self.lbl_opacity = QLabel("88%"); self.lbl_opacity.setFixedWidth(40)
        orow.addWidget(self.slider_opacity, 1); orow.addWidget(self.lbl_opacity)
        self._form_row(lay, "结果窗口透明度", orow)
        self.spin_font_size = QSpinBox(); self.spin_font_size.setRange(10,32); self.spin_font_size.setSuffix(" px")
        self._form_row(lay, "翻译结果字号", self.spin_font_size)
        self.spin_wrap_width = QSpinBox(); self.spin_wrap_width.setRange(300,1200); self.spin_wrap_width.setSingleStep(20); self.spin_wrap_width.setSuffix(" px")
        self._form_row(lay, "结果窗口宽度", self.spin_wrap_width)
        self.chk_top = QCheckBox("结果窗口始终置顶"); lay.addWidget(self.chk_top)
        self.chk_show_src = QCheckBox("默认展开原文对照"); lay.addWidget(self.chk_show_src)
        self.chk_auto_copy = QCheckBox("翻译完成自动复制译文到剪贴板"); lay.addWidget(self.chk_auto_copy)
        lay.addStretch(1); return w

    def _page_history(self):
        w, lay = self._vbox_page()
        self.history_widget = HistoryWidget(self.cfg); lay.addWidget(self.history_widget, 1)
        lr = QHBoxLayout()
        self.spin_hist_limit = QSpinBox(); self.spin_hist_limit.setRange(50,5000); self.spin_hist_limit.setSingleStep(50)
        lr.addWidget(self.spin_hist_limit); lr.addWidget(QLabel("条")); lr.addStretch(1)
        lay.addLayout(lr); return w

    def _page_about(self):
        w, lay = self._vbox_page(); lay.setSpacing(16)
        t = QLabel("屏幕翻译"); t.setStyleSheet("font-size:22px;font-weight:bold;"); lay.addWidget(t)
        d = QLabel("基于腾讯混元 Hy-MT2-1.8B 的屏幕实时翻译工具\n支持截图OCR + 本地离线翻译 / API翻译")
        d.setStyleSheet("font-size:13px;color:#888;"); lay.addWidget(d)
        lay.addStretch(1); return w

    def _load_values(self):
        c = self.cfg
        self.combo_theme.setCurrentIndex({"system":0,"light":1,"dark":2}.get(c.get("theme","system"),0))
        self.combo_lang.setCurrentText(c.get("target_lang","简体中文"))
        self.combo_mode.setCurrentIndex({"area":0,"window":1,"full":2}.get(c.get("capture.default_mode","area"),0))
        self.chk_tray.setChecked(c.get("close_to_tray",True)); self.chk_autostart.setChecked(c.get("autostart",False))
        self.edit_model_path.setText(c.get("local.model_path","")); self.chk_auto_load.setChecked(c.get("local.auto_load",True))
        self.spin_gpu.setValue(c.get("local.n_gpu_layers",0)); self.spin_ctx.setValue(c.get("local.n_ctx",4096)); self.spin_threads.setValue(c.get("local.n_threads",0))
        self.dspin_temp.setValue(c.get("local.temperature",0.7)); self.dspin_top_p.setValue(c.get("local.top_p",0.6))
        self.spin_top_k.setValue(c.get("local.top_k",20)); self.dspin_rep.setValue(c.get("local.repeat_penalty",1.05)); self.spin_max_tok.setValue(c.get("local.max_tokens",2048))
        self.prompt_edit.setPlainText(c.get("local.prompt_template",""))
        eng = c.get("engine","local"); self.combo_engine.setCurrentIndex(1 if eng=="api" else 0); self.sub_stack.setCurrentIndex(1 if eng=="api" else 0)
        self._api_refresh_list()
        si = ["auto","1","1.5","2","3"]; sc = c.get("ocr.scale","auto"); self.combo_ocr_scale.setCurrentIndex(si.index(sc) if sc in si else 0)
        self.chk_merge.setChecked(c.get("ocr.merge_paragraph",True)); self.dspin_min_score.setValue(c.get("ocr.min_score",0.5))
        self.chk_realtime.setChecked(c.get("realtime.enabled",True)); self.spin_interval.setValue(c.get("realtime.interval_ms",500))
        self.spin_settle.setValue(c.get("realtime.settle_ms",800)); self.dspin_diff.setValue(c.get("realtime.diff_threshold",6.0)); self.spin_max_runs.setValue(c.get("realtime.max_runs",0))
        op=c.get("display.opacity",88); self.slider_opacity.setValue(op); self.lbl_opacity.setText(f"{op}%")
        self.spin_font_size.setValue(c.get("display.font_size",14)); self.spin_wrap_width.setValue(c.get("display.wrap_width",560))
        self.chk_top.setChecked(c.get("display.always_top",True)); self.chk_show_src.setChecked(c.get("display.show_source",False)); self.chk_auto_copy.setChecked(c.get("display.auto_copy",False))
        self.spin_hist_limit.setValue(c.get("history_limit",300))

    def _connect_signals(self):
        self.combo_theme.currentIndexChanged.connect(lambda i: self._set("theme",["system","light","dark"][i]))
        self.combo_lang.currentTextChanged.connect(lambda t: self._set("target_lang",t))
        self.combo_mode.currentIndexChanged.connect(lambda i: self._set("capture.default_mode",{0:"area",1:"window",2:"full"}.get(i,"area")))
        self.chk_tray.toggled.connect(lambda b: self._set("close_to_tray",b)); self.chk_autostart.toggled.connect(lambda b: self._set("autostart",b))
        self.he_capture.hotkeyChanged.connect(lambda v: self._set("hotkey_capture",v)); self.he_fullscreen.hotkeyChanged.connect(lambda v: self._set("hotkey_fullscreen",v))
        self.combo_engine.currentIndexChanged.connect(self._on_engine_changed)
        self.edit_model_path.textChanged.connect(lambda t: self._set("local.model_path",t)); self.chk_auto_load.toggled.connect(lambda b: self._set("local.auto_load",b))
        self.spin_gpu.valueChanged.connect(lambda v: self._set("local.n_gpu_layers",v)); self.spin_ctx.valueChanged.connect(lambda v: self._set("local.n_ctx",v))
        self.spin_threads.valueChanged.connect(lambda v: self._set("local.n_threads",v)); self.dspin_temp.valueChanged.connect(lambda v: self._set("local.temperature",v))
        self.dspin_top_p.valueChanged.connect(lambda v: self._set("local.top_p",v)); self.spin_top_k.valueChanged.connect(lambda v: self._set("local.top_k",v))
        self.dspin_rep.valueChanged.connect(lambda v: self._set("local.repeat_penalty",v)); self.spin_max_tok.valueChanged.connect(lambda v: self._set("local.max_tokens",v))
        self.prompt_edit.textChanged.connect(lambda: self._set("local.prompt_template",self.prompt_edit.toPlainText()))
        self.btn_load.clicked.connect(lambda: self.translator.load_local_async()); self.btn_unload.clicked.connect(lambda: self.translator.unload_local())
        self.translator.loadStateChanged.connect(self._on_load_state)
        self.combo_ocr_scale.currentTextChanged.connect(lambda t: self._set("ocr.scale",t)); self.chk_merge.toggled.connect(lambda b: self._set("ocr.merge_paragraph",b))
        self.dspin_min_score.valueChanged.connect(lambda v: self._set("ocr.min_score",v)); self.chk_realtime.toggled.connect(lambda b: self._set("realtime.enabled",b))
        self.spin_interval.valueChanged.connect(lambda v: self._set("realtime.interval_ms",v)); self.spin_settle.valueChanged.connect(lambda v: self._set("realtime.settle_ms",v))
        self.dspin_diff.valueChanged.connect(lambda v: self._set("realtime.diff_threshold",v)); self.spin_max_runs.valueChanged.connect(lambda v: self._set("realtime.max_runs",v))
        self.slider_opacity.valueChanged.connect(lambda v: (self._set("display.opacity",v), self.lbl_opacity.setText(f"{v}%")))
        self.spin_font_size.valueChanged.connect(lambda v: self._set("display.font_size",v)); self.spin_wrap_width.valueChanged.connect(lambda v: self._set("display.wrap_width",v))
        self.chk_top.toggled.connect(lambda b: self._set("display.always_top",b)); self.chk_show_src.toggled.connect(lambda b: self._set("display.show_source",b))
        self.chk_auto_copy.toggled.connect(lambda b: self._set("display.auto_copy",b)); self.spin_hist_limit.valueChanged.connect(lambda v: self._set("history_limit",v))

    def _on_engine_changed(self, idx):
        eng = "api" if idx == 1 else "local"
        self._set("engine", eng); self.sub_stack.setCurrentIndex(idx)
    def _on_load_state(self, text, code):
        c = "#d97706" if code == 0 else ("#16a34a" if code == 1 else "#ef4444")
        self.lbl_model_status.setText(f'<span style="color:{c}">{text}</span>')
        self.engine_status.setText(f"引擎: {self.cfg.get('engine','local')} | {text}")
    def _apply_engine_status(self):
        eng = self.cfg.get("engine","local")
        if eng == "local":
            st = "已就绪" if self.translator.local_ready() else ("加载中..." if self.translator.local_loading() else "未加载")
            self.engine_status.setText(f"引擎: 本地模型 | {st}")
        else:
            apis = self.cfg.get("apis",[]) or []; active = self.cfg.get("active_api","")
            self.engine_status.setText(f"引擎: API | {active or (apis[0].get('name','未配置') if apis else '未配置')}")
    def _browse_model(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择模型文件", "", "GGUF 模型 (*.gguf);;所有文件 (*)")
        if p: self.edit_model_path.setText(p)
    def _apply_preset(self, url, model):
        self.api_url.setText(url); self.api_model.setText(model)
    def _api_refresh_list(self):
        self._api_syncing = True; self.api_list.clear()
        for api in self.cfg.get("apis", []) or []:
            name = api.get("name", "未命名")
            if api.get("name") == self.cfg.get("active_api", ""):
                name = f"● {name}"
            self.api_list.addItem(name)
        self._api_syncing = False
        if self.api_list.count() > 0: self.api_list.setCurrentRow(0)
    def _on_api_selected(self, row):
        if self._api_syncing: return
        apis = self.cfg.get("apis", []) or []
        if 0 <= row < len(apis):
            a = apis[row]
            self.api_name.setText(a.get("name","")); self.api_url.setText(a.get("base_url",""))
            self.api_key.setText(a.get("api_key","")); self.api_model.setText(a.get("model",""))
    def _collect_api_fields(self):
        return {"name":self.api_name.text().strip() or "未命名","base_url":self.api_url.text().strip(),
                "api_key":self.api_key.text().strip(),"model":self.api_model.text().strip()}
    def _add_api(self):
        apis = self.cfg.get("apis",[]) or []; apis.append({"name":f"接口 {len(apis)+1}","base_url":"","api_key":"","model":""})
        self.cfg.set("apis",apis); self._api_refresh_list(); self.api_list.setCurrentRow(self.api_list.count()-1)
    def _del_api(self):
        row = self.api_list.currentRow(); apis = self.cfg.get("apis",[]) or []
        if 0 <= row < len(apis):
            apis.pop(row); self.cfg.set("apis",apis); self._api_refresh_list()
    def _save_api(self):
        row = self.api_list.currentRow(); apis = self.cfg.get("apis",[]) or []
        if 0 <= row < len(apis): apis[row] = self._collect_api_fields(); self.cfg.set("apis",apis); self._api_refresh_list(); self.api_list.setCurrentRow(row)
    def _activate_api(self):
        a = self._collect_api_fields(); apis = self.cfg.get("apis",[]) or []
        if a["name"] not in [x.get("name") for x in apis]: self._save_api()
        self.cfg.set("active_api",a["name"]); self._api_refresh_list(); self._apply_engine_status()
    def _test_api(self):
        a = self._collect_api_fields()
        if not a["base_url"]: self.lbl_api_test.setText("请填写 Base URL"); return
        self.lbl_api_test.setText("测试中..."); self.btn_api_test.setEnabled(False)
        def run():
            try:
                ok, out, err = openai_api.call(a, build_prompt("将以下文本翻译成中文,只需要输出翻译结果:\n\nHello, this is a test.", "简体中文", "Hello, this is a test."), timeout=20)
                self.lbl_api_test.setText(f"✓ {out[:100]}" if ok else f"✗ {err[:200]}")
            except Exception as e: self.lbl_api_test.setText(f"✗ {e}")
            finally: self.btn_api_test.setEnabled(True)
        threading.Thread(target=run, daemon=True).start()
    def refresh_history(self):
        if hasattr(self, 'history_widget'): self.history_widget.refresh()
    def set_autostart_checked(self, v):
        self.chk_autostart.blockSignals(True); self.chk_autostart.setChecked(v); self.chk_autostart.blockSignals(False)
    def closeEvent(self, e):
        if self.cfg.get("close_to_tray", True): e.ignore(); self.hide()
        else: e.accept(); QApplication.instance().quit()
