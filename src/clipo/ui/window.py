"""Presentation only: database requests are exposed as signals."""
from datetime import datetime, timedelta, timezone, time

from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QKeySequence, QShortcut, QIcon
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QVBoxLayout, QWidget,
    QComboBox, QMenu, QToolButton, QAbstractItemView, QDateEdit,
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
    operation_requested = Signal(str, object)

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
        self.view = "all"
        self.current_item = None
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
        nav.addSpacing(18)
        eyebrow = QLabel("YOUR CLIPBOARD")
        eyebrow.setObjectName("eyebrow")
        nav.addWidget(eyebrow)
        group = QButtonGroup(self)
        for title, view in (("All history", "all"), ("Today", "today"), ("Favorites", "favorites"), ("Pinned", "pinned"), ("Text", "text"), ("Images", "image"), ("Links", "url"), ("Files", "files"), ("Code snippets", "snippet"), ("QR history", "qr")):
            button = QPushButton(title)
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setChecked(view == "all")
            group.addButton(button)
            button.clicked.connect(lambda checked=False, value=view: self.set_view(value))
            nav.addWidget(button)
        nav.addStretch()
        quick = QPushButton("Quick clipboard")
        quick.clicked.connect(lambda: self.operation_requested.emit("quick", None))
        nav.addWidget(quick)
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
        library = QToolButton()
        library.setText("Library ▾")
        library.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        library_menu = QMenu(library)
        for title, action in (("New text / snippet", "new_item"), ("QR from entered text", "manual_qr"), ("Export complete history", "export_all"), ("Export current filter / collection", "export_view"), ("Export selected items", "export_selected"), ("Import JSON backup", "import")):
            library_menu.addAction(title, lambda checked=False, value=action: self.operation_requested.emit(value, None))
        library.setMenu(library_menu)
        header.addWidget(library)
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
        filters = QHBoxLayout()
        self.collection = QComboBox()
        self.collection.addItem("All collections", "")
        self.collection.setAccessibleName("Filter by collection")
        self.collection.currentIndexChanged.connect(self.search_changed)
        filters.addWidget(self.collection, 1)
        self.sort = QComboBox()
        for title, value in (("Newest first", "newest"), ("Oldest first", "oldest"), ("Frequently used", "frequent")):
            self.sort.addItem(title, value)
        self.sort.currentIndexChanged.connect(self.search_changed)
        filters.addWidget(self.sort)
        manage = QToolButton()
        manage.setText("Collections")
        manage.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(manage)
        for title, action in (("Create collection", "new_collection"), ("Rename selected collection", "rename_collection"), ("Delete selected collection", "delete_collection"), ("Collection color", "collection_color"), ("Pin / unpin collection", "collection_pin")):
            menu.addAction(title, lambda checked=False, value=action: self.operation_requested.emit(value, self.collection.currentData()))
        manage.setMenu(menu)
        filters.addWidget(manage)
        body.addLayout(filters)
        dates = QHBoxLayout()
        self.date_range = QComboBox()
        self.date_range.addItems(["Any time", "Today", "Yesterday", "Last 7 days", "Last 30 days", "Custom range"])
        self.date_range.setAccessibleName("History date filter")
        dates.addWidget(self.date_range)
        from PySide6.QtCore import QDate
        self.date_start, self.date_end = QDateEdit(QDate.currentDate()), QDateEdit(QDate.currentDate())
        for title, widget in (("Range start", self.date_start), ("Range end (inclusive)", self.date_end)):
            widget.setCalendarPopup(True)
            widget.setAccessibleName(title)
            widget.setVisible(False)
            widget.dateChanged.connect(self.search_changed)
            dates.addWidget(widget)
        self.date_range.currentIndexChanged.connect(self.date_changed)
        dates.addStretch()
        body.addLayout(dates)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        history = QWidget()
        history_layout = QVBoxLayout(history)
        history_layout.setContentsMargins(0, 0, 13, 0)
        self.items = QListWidget()
        self.items.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.items.setIconSize(QSize(72, 54))
        self.items.setAccessibleName("Clipboard history")
        self.items.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
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
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMaximumHeight(250)
        self.image_preview.hide()
        detail_layout.addWidget(self.image_preview)
        self.preview = QPlainTextEdit()
        from clipo.ui.highlighter import CodeHighlighter
        self.highlighter = CodeHighlighter(self.preview.document())
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Select an item to see the full text.")
        self.preview.setAccessibleName("Clipboard item preview")
        detail_layout.addWidget(self.preview, 1)
        self.metadata = QLabel("Nothing selected")
        self.metadata.setTextFormat(Qt.TextFormat.PlainText)
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
        tools = QToolButton()
        tools.setText("Item actions ▾")
        tools.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.action_menu = QMenu(tools)
        self.item_actions = {}
        for title, action in (("Favorite / unfavorite", "favorite"), ("Pin / unpin", "pin"), ("Edit text", "edit_item"), ("Tags and collections", "organize_item"), ("Save image as…", "save_image"), ("Open full image", "view_image")):
            self.item_actions[action] = self.action_menu.addAction(title, lambda checked=False, value=action: self.operate_selected(value))
        for title, action in (("Generate QR", "qr"), ("Extract text (OCR)", "ocr"), ("Save as code snippet", "snippet"), ("Pretty-print JSON", "json_pretty"), ("Minify JSON", "json_minify"), ("Open link / compose email", "open_url")):
            self.item_actions[action] = self.action_menu.addAction(title, lambda checked=False, value=action: self.operate_selected(value))
        tools.setMenu(self.action_menu)
        detail_layout.addWidget(tools)
        self.copy_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        splitter.addWidget(detail)
        splitter.setSizes([490, 320])
        splitter.setChildrenCollapsible(False)
        body.addWidget(splitter, 1)
        footer = QHBoxLayout()
        hint = QLabel("Enter to copy  ·  Ctrl+F to search")
        self.shortcut_hint = hint
        hint.setObjectName("muted")
        footer.addWidget(hint, 1)
        undo = QPushButton("Undo delete")
        undo.clicked.connect(lambda: self.operation_requested.emit("undo", None))
        footer.addWidget(undo)
        clear = QPushButton("Clear history…")
        clear.clicked.connect(self.confirm_clear)
        footer.addWidget(clear)
        body.addLayout(footer)
        self.statusBar().showMessage("Starting history…")
        self.key_actions = {"search": self.search.setFocus, "quit": self.request_quit, "pin": lambda: self.operate_selected("pin"), "delete": self.delete_selected,
            "private": self.private_button.toggle, "pause": self.pause_button.toggle, "qr": lambda: self.operate_selected("qr")}
        self.key_shortcuts = {}
        from clipo.config.settings import Settings
        self.apply_keys(Settings().key_bindings)

    def apply_keys(self, bindings):
        self.search.setPlaceholderText("Search your clipboard…  " + bindings.get("search", ""))
        self.shortcut_hint.setText("Enter to copy  ·  " + (bindings.get("search", "") or "Search box") + " to search")
        for name, value in bindings.items():
            if name in self.key_shortcuts:
                self.key_shortcuts[name].setKey(QKeySequence(value))
            else:
                shortcut = QShortcut(QKeySequence(value), self.items if name in ("pin", "delete") else self, activated=self.key_actions[name])
                if name in ("pin", "delete"):
                    shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                self.key_shortcuts[name] = shortcut

    def operate_selected(self, action):
        if self.selected_id is not None:
            self.operation_requested.emit(action, self.selected_id)

    def show_collections(self, names):
        current = self.collection.currentData()
        self.collection.blockSignals(True)
        self.collection.clear()
        self.collection.addItem("All collections", "")
        for entry in names:
            from PySide6.QtGui import QPixmap, QColor
            pixmap = QPixmap(12, 12)
            pixmap.fill(QColor(entry["color"]))
            name = entry["name"]
            self.collection.addItem(QIcon(pixmap), ("★ " if entry["is_pinned"] else "") + name, name)
        index = self.collection.findData(current)
        self.collection.setCurrentIndex(max(0, index))
        self.collection.blockSignals(False)

    def set_view(self, view):
        self.view = "all" if view == "today" else view
        self.set_filter(view == "today")

    def date_changed(self):
        custom = self.date_range.currentIndex() == 5
        self.date_start.setVisible(custom)
        self.date_end.setVisible(custom)
        self.search_changed()

    def history_query(self):
        now = datetime.now().astimezone()
        begin, end = None, None
        index = self.date_range.currentIndex()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if index == 1:
            begin = midnight
        elif index == 2:
            begin, end = midnight - timedelta(days=1), midnight
        elif index in (3, 4):
            begin = now - timedelta(days=7 if index == 3 else 30)
        elif index == 5:
            begin = datetime.combine(self.date_start.date().toPython(), time.min).astimezone()
            end = datetime.combine(self.date_end.date().toPython() + timedelta(days=1), time.min).astimezone()
        return HistoryQuery(self.search.text(), self.today, self.offset, view=self.view,
            collection=self.collection.currentData() or "", sort=self.sort.currentData(),
            since=begin.astimezone(timezone.utc).isoformat() if begin else "", until=end.astimezone(timezone.utc).isoformat() if end else "")

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
        self.query_requested.emit(self.history_query(), self.generation)

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
            flags = (" ★" if item.is_favorite else "") + (" · PINNED" if item.is_pinned else "")
            entry = QListWidgetItem(f"{item.title or text}\n\n{item.content_type.upper()}{flags}  ·  {timestamp}")
            if item.image_path:
                from pathlib import Path
                path = Path(item.image_path)
                entry.setIcon(QIcon(str(path.parent / "thumbnails" / path.name)))
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
        self.current_item = None
        self.image_preview.clear()
        self.image_preview.hide()
        self.preview.show()
        self.copy_button.setEnabled(current is not None)
        self.delete_button.setEnabled(current is not None)
        self.preview.clear()
        for action in self.item_actions.values():
            action.setEnabled(False)
        self.metadata.setText("Loading…" if current else "Nothing selected")
        if current:
            self.preview_requested.emit(self.selected_id)

    def show_preview(self, item):
        if item is None or item.id != self.selected_id:
            return
        self.preview_id = item.id
        self.current_item = item
        for action in self.item_actions.values():
            action.setEnabled(True)
        for action in ("save_image", "view_image", "ocr"):
            self.item_actions[action].setEnabled(item.content_type == "image")
        for action in ("edit_item", "snippet"):
            self.item_actions[action].setEnabled(item.content_type != "image")
        for action in ("json_pretty", "json_minify"):
            self.item_actions[action].setEnabled(item.content_text.strip().startswith(("{", "[")))
        self.item_actions["open_url"].setEnabled(item.content_type in ("url", "email"))
        self.item_actions["qr"].setEnabled(bool(item.ocr_text) if item.content_type == "image" else bool(item.content_text))
        # Keep painting responsive with large payloads; restore always uses full storage text.
        self.preview.setPlainText(item.content_text[:50000])
        self.highlighter.set_language(item.language)
        when = datetime.fromisoformat(item.created_at).astimezone().strftime("%d %B %Y, %H:%M:%S")
        suffix = "\nPreview limited to 50,000 characters. Copy restores the full text." if len(item.content_text) > 50000 else ""
        self.metadata.setText(f"{item.content_type.title()} · {len(item.content_text):,} characters\n{when}\nTags: {item.tags or '—'}\nCollections: {item.collections or '—'}{suffix}")

    def show_image(self, item, image):
        if item.id != self.selected_id:
            return
        from PySide6.QtGui import QPixmap
        self.show_preview(item)
        self.image_preview.show()
        self.image_preview.setPixmap(QPixmap.fromImage(image).scaled(300, 240, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.preview.setPlainText(item.ocr_text[:50000] or "Use Item actions to save, view, or extract text from this image.")

    def restore_selected(self):
        if self.selected_id is not None:
            self.restore_requested.emit(self.selected_id)

    def delete_selected(self):
        for entry in self.items.selectedItems():
            self.delete_requested.emit(entry.data(Qt.ItemDataRole.UserRole))

    def confirm_clear(self):
        if QMessageBox.question(self, "Clear clipboard history?", "Delete all saved items? This cannot be undone. The current system clipboard will remain unchanged.",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                QMessageBox.StandardButton.Cancel) == QMessageBox.StandardButton.Yes:
            self.clear_requested.emit()

