import json
import ssl
import socket
import urllib.request
import urllib.error
import pytest
from clipo.services.recognition import format_code


def test_code_formatters_preserve_comments_and_do_not_execute(tmp_path):
    text = "# keep this comment\ndef hello( name ):\n return name\n"
    formatted = format_code(text, "Python")
    assert "# keep this comment" in formatted and "def hello(name):" in formatted
    assert "SELECT" in format_code("select * from things where id=1", "SQL")
    with pytest.raises(ValueError):
        format_code("not valid python !", "Python")
    assert not (tmp_path / "executed").exists()


def test_bridge_enforces_privacy_validation_and_limits(qtbot):
    from clipo.clipboard.gnome_bridge import GnomeBridge
    from clipo.clipboard.monitor import ClipboardMonitor
    from clipo.config.settings import Settings
    from test_clipboard import ExternalClipboard
    monitor = ClipboardMonitor(ExternalClipboard(), 1024)
    monitor.policy = Settings()
    monitor.enabled = True
    bridge = GnomeBridge(monitor)
    assert not bridge.available  # Offscreen tests do not claim a live desktop's service.
    received = []
    bridge.payload.connect(received.append)
    try:
        assert bridge.Ingest(json.dumps({"kind": "text", "text": "hello বাংলা", "source": "Editor"}))
        assert received[0]["text"] == "hello বাংলা"
        monitor.set_private(True)
        assert not bridge.Ingest(json.dumps({"kind": "text", "text": "private", "source": "Editor"}))
        assert not json.loads(bridge.Status("Editor"))["enabled"]
        monitor.set_private(False)
        assert not bridge.Ingest(json.dumps({"kind": "text", "text": "Authorization: Bearer secret-token", "source": "Editor"}))
        assert not bridge.Ingest(json.dumps({"kind": "text", "text": "x" * 2000, "source": "Editor"}))
        assert not bridge.Ingest(json.dumps({"kind": "files", "text": "javascript:alert(1)", "source": "Files"}))
        assert len(received) == 1
        assert bridge.Ingest(json.dumps({"kind": "files", "text": "https://ubuntu.com\r\n", "source": "Browser"}))
        assert received[-1] == {"kind": "text", "text": "https://ubuntu.com"}
    finally:
        bridge.close()


def test_tls_share_requires_explicit_receipt_is_one_time_and_escapes_content():
    from clipo.services.sharing import ShareSession
    try:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
    except PermissionError:
        pytest.skip("Sandbox blocks local network sockets")
    session = ShareSession("127.0.0.1", b"<script>alert('test')</script>\nsecret", lifetime=10)
    context = ssl.create_default_context(cadata=session.certificate.decode())
    try:
        with urllib.request.urlopen(session.url, context=context) as response:
            landing = response.read()
            assert b"secret" not in landing and b"Receive item" in landing
        assert session.data is not None
        request = urllib.request.Request(session.url, data=b"", method="POST")
        with urllib.request.urlopen(request, context=context) as response:
            body = response.read()
            assert b"&lt;script&gt;" in body and b"<script>" not in body
            assert response.headers["Cache-Control"] == "no-store"
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, context=context)
        assert error.value.code == 410
        assert session.data is None
    finally:
        session.close()


@pytest.mark.parametrize("host", ["0.0.0.0", "8.8.8.8", "224.0.0.1"])
def test_share_rejects_public_or_wildcard_binding(host):
    from clipo.services.sharing import ShareSession
    with pytest.raises(ValueError):
        ShareSession(host, b"text")


def test_worker_encrypt_lock_unlock_and_no_plain_blob_files(tmp_path):
    from clipo.core.worker import HistoryWorker
    from clipo.models.item import HistoryQuery
    from clipo.config.settings import Settings
    worker = HistoryWorker(tmp_path / "history.sqlite3", 100, 1024, Settings())
    failures, migrated = [], []
    worker.error.connect(failures.append)
    worker.encryption_ready.connect(migrated.append)
    worker.initialize()
    worker.execute("capture", "secret migration")
    worker.execute("encrypt", ("a long test passphrase", True))
    assert migrated == [True]
    assert worker.repository.vault is not None
    worker.execute("remove_plain", None)
    assert not (tmp_path / "history.sqlite3").exists()
    worker.execute("configure", Settings(encrypted=False))  # Stale queued UI snapshot.
    assert worker.settings.encrypted and worker.repository.vault is not None
    worker.execute("lock", None)
    assert worker.repository is None and worker.password is None
    worker.execute("unlock", "a long test passphrase")
    assert worker.repository.page(HistoryQuery()).items[0].content_text == "secret migration"
    assert not failures
    worker.close()


def test_gui_vault_lock_discards_stale_preview_and_unlocks(qtbot, qapp, tmp_path):
    from clipo.application.controller import Controller
    from clipo.config.settings import Settings
    from clipo.storage.repository import HistoryRepository
    from clipo.models.item import HistoryQuery
    from PySide6.QtGui import QIcon
    password = "a long GUI test passphrase"
    repo = HistoryRepository(tmp_path / "vault/history.sqlite3", password=password)
    repo.add("private GUI history", 100)
    stale = repo.page(HistoryQuery())
    repo.close()
    controller = Controller(qapp, Settings(encrypted=True), tmp_path / "settings.json", tmp_path, QIcon(), password=password)
    qtbot.addWidget(controller.window)
    try:
        qtbot.waitUntil(lambda: controller.window.preview.toPlainText() == "private GUI history")
        controller.operation("lock", None)
        assert controller.locked and not controller.monitor.enabled
        assert controller.window.items.count() == 0 and not controller.window.preview.toPlainText()
        controller.on_page(stale, controller.window.generation)
        assert controller.window.items.count() == 0
        controller.command.emit("unlock", password)
        qtbot.waitUntil(lambda: not controller.locked)
        qtbot.waitUntil(lambda: controller.window.preview.toPlainText() == "private GUI history")
    finally:
        controller.shutdown()
        qapp.aboutToQuit.disconnect(controller.shutdown)
