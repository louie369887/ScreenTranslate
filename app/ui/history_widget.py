from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import clear_history, load_history


class HistoryWidget(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索原文 / 译文…")
        self.search.setClearButtonEnabled(True)
        bar.addWidget(self.search, 1)
        self.clear_btn = QPushButton("清空历史")
        self.clear_btn.setObjectName("dangerBtn")
        bar.addWidget(self.clear_btn)
        lay.addLayout(bar)

        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.setAlternatingRowColors(False)
        lay.addWidget(self.list, 1)

        self.search.textChanged.connect(self.refresh)
        self.clear_btn.clicked.connect(self._clear)

    def _clear(self):
        ret = QMessageBox.question(self, "清空历史", "确定要清空全部翻译历史吗？",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret == QMessageBox.Yes:
            clear_history()
            self.refresh()

    def refresh(self):
        keyword = self.search.text().strip().lower()
        items = load_history()
        limit = max(50, int(self._cfg.get("history_limit", 300)))
        shown = 0
        self.list.clear()
        for it in items:
            if shown >= limit:
                break
            src = (it.get("source") or "").replace("\n", " ")
            out = (it.get("result") or "").replace("\n", " ")
            time_s = it.get("time") or ""
            line = f"[{time_s}]  {src}\n→ {out}"
            if keyword and keyword not in line.lower():
                continue
            from PySide6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(line[:500])
            item.setData(Qt.UserRole, it)
            self.list.addItem(item)
            shown += 1
