"""Searchable quick access window, separate from the main history view."""
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QCursor, QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout
from clipo.models.item import HistoryQuery


class QuickPopup(QDialog):
    query_requested = Signal(object, int)
    restore_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle("Quick Clipo")
        self.resize(500, 480)
        self.generation = 0
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Quick clipboard · Enter to copy"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Find a clip…")
        layout.addWidget(self.search)
        self.items = QListWidget()
        self.items.setIconSize(QSize(64, 48))
        self.items.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.items)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(120)
        self.search.textChanged.connect(self.schedule_search)
        self.timer.timeout.connect(self.refresh)
        self.search.returnPressed.connect(self.copy)
        self.items.itemActivated.connect(lambda _: self.copy())
        down = QShortcut(QKeySequence("Down"), self.search, activated=self.focus_list)
        down.setContext(Qt.ShortcutContext.WidgetShortcut)

    def schedule_search(self):
        self.generation += 1
        self.timer.start()

    def focus_list(self):
        self.items.setFocus()
        if self.items.currentRow() < 0:
            self.items.setCurrentRow(0)

    def reveal(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        rect = screen.availableGeometry()
        self.move(max(rect.left(), min(QCursor.pos().x(), rect.right() - self.width())),
                  max(rect.top(), min(QCursor.pos().y(), rect.bottom() - self.height())))
        self.search.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()
        self.refresh()

    def refresh(self):
        self.generation += 1
        self.query_requested.emit(HistoryQuery(text=self.search.text(), limit=30), self.generation)

    def show_page(self, page, generation):
        if generation != self.generation:
            return
        self.items.clear()
        for item in page.items:
            entry = QListWidgetItem(f"{item.content_type.upper()} · {item.title or ' '.join(item.content_text.split())[:140]}")
            if item.image_path:
                from pathlib import Path
                path = Path(item.image_path)
                entry.setIcon(QIcon(str(path.parent / "thumbnails" / path.name)))
            entry.setData(Qt.ItemDataRole.UserRole, item.id)
            self.items.addItem(entry)
        self.items.setCurrentRow(0)

    def copy(self):
        if self.items.currentItem():
            self.restore_requested.emit(self.items.currentItem().data(Qt.ItemDataRole.UserRole))
            self.hide()
