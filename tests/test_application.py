from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
import pytest

from clipo.application.controller import Controller
from clipo.config.settings import Settings
from clipo.models.item import HistoryQuery


@pytest.mark.parametrize('block_sensitive', [False, True])
def test_vscode_clipboard_reaches_real_worker_thread_and_persists(qtbot, qapp, tmp_path, block_sensitive):
    from html import escape
    from pathlib import Path
    from test_clipboard import ExternalClipboard
    from clipo.storage.repository import HistoryRepository
    text = (Path(__file__).parent / 'fixtures/vscode_worker.txt').read_text()
    if not block_sensitive:
        text += '\n# password="example-for-default-filter-test"\n'
    html = '<pre>' + escape(text) + '</pre>'
    controller = Controller(qapp, Settings(block_sensitive=block_sensitive), tmp_path / 'settings.json', tmp_path / 'data', QIcon())
    qtbot.addWidget(controller.window)
    clipboard = ExternalClipboard()
    controller.monitor.clipboard = clipboard
    clipboard.dataChanged.connect(controller.monitor.capture)
    try:
        qtbot.waitUntil(lambda: controller.monitor.enabled)
        clipboard.mime.setHtml(html)
        with qtbot.waitSignal(controller.worker.changed):
            clipboard.setText(text)
        qtbot.waitUntil(lambda: controller.window.items.count() == 1)
        qtbot.waitUntil(lambda: controller.window.current_item is not None)
        assert controller.window.current_item.content_text == text
    finally:
        controller.shutdown()
        qapp.aboutToQuit.disconnect(controller.shutdown)
    repository = HistoryRepository(tmp_path / 'data/history.sqlite3')
    try:
        assert repository.get(1).content_text == text
        assert repository.get(1).content_html == html
    finally:
        repository.close()


def test_worker_to_window_restore_search_and_restart(qtbot, qapp, tmp_path):
    controller = Controller(qapp, Settings(), tmp_path / "settings.json", tmp_path / "data", QIcon())
    qtbot.addWidget(controller.window)
    try:
        qtbot.waitUntil(lambda: controller.monitor.enabled)
        with qtbot.waitSignal(controller.worker.changed):
            controller.command.emit("capture", "Full original text 👋\nsecond line")
        qtbot.waitUntil(lambda: controller.window.items.count() == 1)
        qtbot.waitUntil(lambda: "Full original text" in controller.window.preview.toPlainText())
        with qtbot.waitSignal(controller.worker.item_ready):
            qtbot.mouseClick(controller.window.copy_button, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda: qapp.clipboard().text() == "Full original text 👋\nsecond line")
        controller.window.search.setText("nothing matches")
        qtbot.waitUntil(lambda: controller.window.total == 0)
        controller.window.search.clear()
        qtbot.waitUntil(lambda: controller.window.total == 1)
        controller.window.hide()
        controller.shortcuts.activated.emit()
        assert controller.window.isVisible()
        assert not controller.popup.isVisible()
        qtbot.mouseClick(controller.window.pause_button, Qt.MouseButton.LeftButton)
        assert controller.monitor.paused
        qtbot.mouseClick(controller.window.private_button, Qt.MouseButton.LeftButton)
        assert controller.monitor.private
        assert Settings.load(tmp_path / "settings.json").private
    finally:
        controller.shutdown()
        qapp.aboutToQuit.disconnect(controller.shutdown)
    # SQLite was closed cleanly on its worker thread.
    from clipo.storage.repository import HistoryRepository
    repo = HistoryRepository(tmp_path / "data" / "history.sqlite3")
    assert repo.page(HistoryQuery()).total == 1
    repo.close()


def test_delete_shortcut_does_not_delete_items_while_typing(qtbot):
    from clipo.ui.window import MainWindow
    from clipo.models.item import ClipboardItem, HistoryPage
    window = MainWindow("Test display")
    qtbot.addWidget(window)
    window.show()
    window.activateWindow()
    window.show_page(HistoryPage(HistoryQuery(), (ClipboardItem(1, "saved", "hash", "2026-11-04T00:00:00+00:00"),), 1), 0)
    deleted = []
    window.delete_requested.connect(deleted.append)
    window.search.setText("abc")
    window.search.setCursorPosition(0)
    window.search.setFocus()
    qtbot.keyClick(window.search, Qt.Key.Key_Delete)
    assert window.search.text() == "bc" and not deleted


def test_row_qr_action_shares_its_own_item_without_restoring(qtbot):
    from clipo.ui.window import MainWindow
    from clipo.models.item import ClipboardItem, HistoryPage
    window = MainWindow("Test display")
    qtbot.addWidget(window)
    window.show()
    items = (
        ClipboardItem(1, "first", "one", "2026-11-04T00:00:00+00:00"),
        ClipboardItem(2, "second", "two", "2026-11-04T00:00:00+00:00"),
        ClipboardItem(3, "image", "three", "2026-11-04T00:00:00+00:00", content_type="image"),
    )
    window.show_page(HistoryPage(HistoryQuery(), items, 3), 0)
    operations, restored = [], []
    window.operation_requested.connect(lambda action, item_id: operations.append((action, item_id)))
    window.restore_requested.connect(restored.append)
    buttons = [button for _, button in window.items._qr_buttons]
    qtbot.waitUntil(buttons[1].isVisible)
    qtbot.mouseClick(buttons[1], Qt.MouseButton.LeftButton)
    assert operations == [("qr", 2)]
    assert window.selected_id == 1
    assert not restored
    assert len(buttons) == 2  # Images without OCR have no QR action.
    # Replacing a search page removes old row actions as well as the old rows.
    window.show_page(HistoryPage(HistoryQuery(), items[:1], 1), 0)
    assert len(window.items._qr_buttons) == 1


def test_qr_actions_only_appear_for_shareable_text(qtbot):
    from dataclasses import replace
    from clipo.ui.window import MainWindow
    from clipo.models.item import ClipboardItem, HistoryPage
    window = MainWindow("Test display")
    qtbot.addWidget(window)
    item = ClipboardItem(1, "some text", "hash", "2026-11-05T00:00:00+00:00")
    items = (
        item,
        replace(item, id=2, content_type="snippet"),
        replace(item, id=3, content_type="url"),
        replace(item, id=4, content_type="image"),
        replace(item, id=5, content_type="files"),
        replace(item, id=6, content_type="image", ocr_text="extracted text"),
        replace(item, id=7, content_text="  "),
    )
    window.show_page(HistoryPage(HistoryQuery(), items, len(items)), 0)
    assert [row.data(Qt.ItemDataRole.UserRole) for row, _ in window.items._qr_buttons] == [1, 2, 3, 6]
