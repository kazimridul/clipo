"""Presentation only: database requests are exposed as signals."""
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from clipo.models.item import HistoryQuery


class MainWindow(QMainWindow):
    query_requested = Signal(object, int)
    preview_requested = Signal(int)
    restore_requested = Signal(int)
    delete_requested = Signal(int)
    clear_requested = Signal()
    pause_requested = Signal(bool)
    private_requested = Signal(bool)
    settings_requested = Signal()

    def __init__(self, platform_message: str):
        super().__init__()
        self.setWindowTitle("Clipo — your clipboard, remembered")
        self.resize(1220, 790)
        self.setMinimumSize(850, 570)
        self.hide_to_tray = False
        self.offset = 0
        self.total = 0
        self.generation = 0
        self.today = False
        self.selected_id = None
        self.preview_id = None
        self.setAcceptDrops(False)

        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setCentralWidget(root)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(202)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(20, 27, 20, 20)
        brand = QLabel("▣  clipo")
        brand.setObjectName("brand")
        nav.addWidget(brand)
        subtitle = QLabel("A little less remembering.")
        subtitle.setObjectName("muted")
        nav.addWidget(subtitle)
        nav.addSpacing(35)
        eyebrow = QLabel("YOUR CLIPBOARD")
        eyebrow.setObjectName("eyebrow")
        nav.addWidget(eyebrow)
        group = QButtonGroup(self)
        for title, today in (("All history", False), ("Today", True)):
            button = QPushButton(title)
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setChecked(not today)
            group.addButton(button)
            button.clicked.connect(lambda checked=False, value=today: self.set_filter(value))
            nav.addWidget(button)
        nav.addStretch()
        self.private_button = QPushButton("Private mode")
        self.private_button.setCheckable(True)
        self.private_button.toggled.connect(self.private_requested)
        self.private_button.setToolTip("Stop recording until you explicitly turn private mode off")
        nav.addWidget(self.private_button)
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(self.settings_requested)
        nav.addWidget(settings_button)
        foot = QLabel("LOCAL STORAGE\nOnly on this device")
        foot.setObjectName("eyebrow")
        nav.addSpacing(14)
        nav.addWidget(foot)
        outer.addWidget(sidebar)

        body = QVBoxLayout()
        body.setContentsMargins(27, 27, 27, 16)
        body.setSpacing(16)
        outer.addLayout(body, 1)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        self.heading = QLabel("Clipboard history")
        self.heading.setObjectName("heading")
        titles.addWidget(self.heading)
        self.summary = QLabel("Copy something. Find it here.")
        self.summary.setObjectName("muted")
        titles.addWidget(self.summary)
        header.addLayout(titles, 1)
        self.pause_button = QPushButton("Pause capture")
        self.pause_button.setCheckable(True)
        self.pause_button.toggled.connect(self.pause_requested)
        header.addWidget(self.pause_button)
        body.addLayout(header)
        self.notice = QLabel(platform_message)
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        body.addWidget(self.notice)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search your clipboard…                       Ctrl+F")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Search clipboard history")
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search.textChanged.connect(self.schedule_search)
        self.search_timer.timeout.connect(self.search_changed)
        body.addWidget(self.search)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        history = QWidget()
        history_layout = QVBoxLayout(history)
        history_layout.setContentsMargins(0, 0, 13, 0)
        self.items = QListWidget()
        self.items.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.items.setAccessibleName("Clipboard history")
        self.items.currentItemChanged.connect(self.selection_changed)
        self.items.itemActivated.connect(lambda item: self.restore_selected())
        history_layout.addWidget(self.items)
        self.empty = QLabel("Your clipboard starts here\n\nCopy text in another app to save it.\nClipo keeps it on this device.")
        self.empty.setObjectName("muted")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        history_layout.addWidget(self.empty)
        pager = QHBoxLayout()
        self.previous = QPushButton("← Newer")
        self.next = QPushButton("Older →")
        self.previous.clicked.connect(lambda: self.paginate(-100))
        self.next.clicked.connect(lambda: self.paginate(100))
        pager.addWidget(self.previous)
        pager.addStretch()
        pager.addWidget(self.next)
        history_layout.addLayout(pager)
        splitter.addWidget(history)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(18, 0, 0, 0)
        eyebrow = QLabel("PREVIEW")
        eyebrow.setObjectName("eyebrow")
        detail_layout.addWidget(eyebrow)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Select an item to see the full text.")
        self.preview.setAccessibleName("Clipboard item preview")
        detail_layout.addWidget(self.preview, 1)
        self.metadata = QLabel("Nothing selected")
        self.metadata.setObjectName("metadata")
        self.metadata.setWordWrap(True)
        detail_layout.addWidget(self.metadata)
        self.copy_button = QPushButton("Copy to clipboard    ↵")
        self.copy_button.setObjectName("primary")
        self.copy_button.clicked.connect(self.restore_selected)
        detail_layout.addWidget(self.copy_button)
        self.delete_button = QPushButton("Delete item")
        self.delete_button.clicked.connect(self.delete_selected)
        detail_layout.addWidget(self.delete_button)
        self.copy_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        splitter.addWidget(detail)
        splitter.setSizes([490, 320])
        splitter.setChildrenCollapsible(False)
        body.addWidget(splitter, 1)
        footer = QHBoxLayout()
        hint = QLabel("Enter to copy  ·  Ctrl+F to search")
        hint.setObjectName("muted")
        footer.addWidget(hint, 1)
        clear = QPushButton("Clear history…")
        clear.clicked.connect(self.confirm_clear)
        footer.addWidget(clear)
        body.addLayout(footer)
        self.statusBar().showMessage("Starting history…")
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.search.setFocus)
        QShortcut(QKeySequence("Ctrl+Q"), self, activated=self.request_quit)

    def request_quit(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self.hide_to_tray:
            self.hide()
            event.ignore()
        else:
            event.accept()

    def set_filter(self, today):
        self.today = today
        self.heading.setText("Today" if today else "Clipboard history")
        self.offset = 0
        self.refresh()

    def schedule_search(self):
        # Invalidate in-flight results as soon as the user types.
        self.generation += 1
        self.search_timer.start()

    def search_changed(self):
        self.offset = 0
        self.refresh()

    def paginate(self, delta):
        self.offset = max(0, self.offset + delta)
        self.refresh()

    def refresh(self):
        self.generation += 1
        self.query_requested.emit(HistoryQuery(self.search.text(), self.today, self.offset), self.generation)

    def show_page(self, page, generation):
        if generation != self.generation:
            return
        if not page.items and page.total and self.offset:
            self.offset = max(0, ((page.total - 1) // 100) * 100)
            self.refresh()
            return
        previous = self.selected_id
        self.items.clear()
        self.total = page.total
        for item in page.items:
            timestamp = datetime.fromisoformat(item.created_at).astimezone().strftime("%b %d · %H:%M")
            text = " ".join(item.content_text.split())[:115]
            entry = QListWidgetItem(f"{text}\n\nTEXT  ·  {timestamp}")
            entry.setData(Qt.ItemDataRole.UserRole, item.id)
            self.items.addItem(entry)
            if item.id == previous:
                self.items.setCurrentItem(entry)
        if self.items.currentRow() < 0 and self.items.count():
            self.items.setCurrentRow(0)
        self.empty.setVisible(not page.items)
        self.items.setVisible(bool(page.items))
        self.empty.setText("No matching items\n\nTry a different search or filter." if self.search.text() or self.today else
                           "Your clipboard starts here\n\nCopy text in another app to save it.\nClipo keeps it on this device.")
        self.summary.setText(f"{page.total:,} {'item' if page.total == 1 else 'items'} · stored on this device")
        self.previous.setEnabled(self.offset > 0)
        self.next.setEnabled(self.offset + len(page.items) < page.total)

    def selection_changed(self, current, previous):
        self.selected_id = current.data(Qt.ItemDataRole.UserRole) if current else None
        self.preview_id = None
        self.copy_button.setEnabled(current is not None)
        self.delete_button.setEnabled(current is not None)
        self.preview.clear()
        self.metadata.setText("Loading…" if current else "Nothing selected")
        if current:
            self.preview_requested.emit(self.selected_id)

    def show_preview(self, item):
        if item is None or item.id != self.selected_id:
            return
        self.preview_id = item.id
        # Keep painting responsive with large payloads; restore always uses full storage text.
        self.preview.setPlainText(item.content_text[:50000])
        when = datetime.fromisoformat(item.created_at).astimezone().strftime("%d %B %Y, %H:%M:%S")
        suffix = "\nPreview limited to 50,000 characters. Copy restores the full text." if len(item.content_text) > 50000 else ""
        self.metadata.setText(f"Plain text · {len(item.content_text):,} characters\n{when}{suffix}")

    def restore_selected(self):
        if self.selected_id is not None:
            self.restore_requested.emit(self.selected_id)

    def delete_selected(self):
        if self.selected_id is not None:
            self.delete_requested.emit(self.selected_id)

    def confirm_clear(self):
        if QMessageBox.question(self, "Clear clipboard history?", "Delete all saved items? This cannot be undone. The current system clipboard will remain unchanged.",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Yes:
            self.clear_requested.emit()

