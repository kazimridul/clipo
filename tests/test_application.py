from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from clipo.application.controller import Controller
from clipo.config.settings import Settings
from clipo.models.item import HistoryQuery


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
        assert qapp.clipboard().text() == "Full original text 👋\nsecond line"
        controller.window.search.setText("nothing matches")
        qtbot.waitUntil(lambda: controller.window.total == 0)
        controller.window.search.clear()
        qtbot.waitUntil(lambda: controller.window.total == 1)
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
