"""Application entry point and single-instance desktop activation."""
import argparse
import hashlib
import logging
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from clipo import __version__
from clipo.application.controller import Controller
from clipo.config.settings import Settings, private_directory, xdg_path
from clipo.system.tray import Tray
from clipo.ui.theme import apply_theme


def main(argv=None):
    parser = argparse.ArgumentParser(description="Clipo — local Linux clipboard history")
    parser.add_argument("--version", action="version", version=f"Clipo {__version__}")
    parser.add_argument("--data-dir", type=Path, help="Use a separate history directory")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    app = QApplication([sys.argv[0]])
    app.setApplicationName("Clipo")
    app.setOrganizationName("Clipo")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    try:
        data_path = private_directory(args.data_dir.resolve() if args.data_dir else xdg_path("XDG_DATA_HOME", ".local/share"))
        config_path = (data_path if args.data_dir else xdg_path("XDG_CONFIG_HOME", ".config")) / "settings.json"
        settings = Settings.load(config_path)
    except (OSError, ValueError, TypeError):
        QMessageBox.critical(None, "Clipo could not start", "The settings or data directory could not be read. Check permissions and settings.json. Your history has not been changed.")
        return 1
    socket_name = "clipo-" + hashlib.sha256(str(data_path).encode()).hexdigest()[:24]
    lock = QLockFile(str(data_path / "instance.lock"))
    if not lock.tryLock(100):
        client = QLocalSocket()
        client.connectToServer(socket_name)
        if client.waitForConnected(1000):
            client.write(b"show")
            client.waitForBytesWritten(1000)
            client.disconnectFromServer()
            return 0
        QMessageBox.warning(None, "Clipo is already running", "Another Clipo instance is starting or owns this data directory.")
        return 1
    QLocalServer.removeServer(socket_name)
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    if not server.listen(socket_name):
        QMessageBox.critical(None, "Clipo could not start", "The local activation socket could not be opened.")
        return 1
    icon = QIcon(str(Path(__file__).parents[1] / "resources" / "clipo.svg"))
    app.setWindowIcon(icon)
    apply_theme(app, settings.theme)
    controller = Controller(app, settings, config_path, data_path, icon)
    # Give Python regular opportunities to dispatch terminal/process signals.
    heartbeat = QTimer()
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start(250)
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: app.quit())

    def activate():
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            socket.close()
            socket.deleteLater()
        Tray.reveal(controller.window)

    server.newConnection.connect(activate)
    controller.window.show()
    result = app.exec()
    server.close()
    lock.unlock()
    return result
