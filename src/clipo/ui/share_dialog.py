"""A transfer starts only when the user explicitly presses Create link."""
import ipaddress
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtNetwork import QNetworkInterface
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QLineEdit, QSpinBox
from clipo.services.sharing import ShareSession
from clipo.services.qr import generate_qr


class ShareDialog(QDialog):
    def __init__(self, data, kind, runner, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Share once with a phone")
        self.resize(640, 650)
        self.data, self.kind, self.runner = data, kind, runner
        self.session = None
        self.alive = True
        self.serial = 0
        layout = QVBoxLayout(self)
        info = QLabel("Both devices must be on the same local network. No transfer server starts until you create a link. The link expires and can be received once.")
        info.setWordWrap(True)
        layout.addWidget(info)
        row = QHBoxLayout()
        self.host = QComboBox()
        for interface in QNetworkInterface.allInterfaces():
            for entry in interface.addressEntries():
                address = entry.ip().toString()
                try:
                    ip = ipaddress.ip_address(address)
                    if ip.version == 4 and ip.is_private and not ip.is_loopback:
                        self.host.addItem(f"{interface.humanReadableName()} · {address}", address)
                except ValueError:
                    pass
        row.addWidget(self.host, 1)
        self.lifetime = QSpinBox()
        self.lifetime.setRange(10, 600)
        self.lifetime.setValue(60)
        self.lifetime.setSuffix(" seconds")
        row.addWidget(self.lifetime)
        layout.addLayout(row)
        self.create = QPushButton("Create encrypted local link")
        self.create.clicked.connect(self.start)
        self.create.setEnabled(self.host.count() > 0)
        layout.addWidget(self.create)
        self.image = QLabel()
        from PySide6.QtCore import Qt
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image)
        self.url = QLineEdit()
        self.url.setReadOnly(True)
        layout.addWidget(self.url)
        self.message = QLabel("Choose your LAN interface." if self.host.count() else "No private IPv4 interface is available. Connect to Wi-Fi or Ethernet first.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.fingerprint = QLabel()
        self.fingerprint.setWordWrap(True)
        self.fingerprint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.fingerprint)
        stop = QPushButton("Revoke link")
        stop.clicked.connect(self.stop)
        layout.addWidget(stop)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)

    def start(self):
        self.stop()
        serial = self.serial
        host, lifetime, data, kind = self.host.currentData(), self.lifetime.value(), self.data, self.kind
        self.create.setEnabled(False)
        self.message.setText("Creating local TLS transfer…")
        def complete(session):
            if not self.alive or serial != self.serial:
                session.close()
                return
            self.session = session
            self.url.setText(session.url)
            self.fingerprint.setText("Phone browsers will ask about this local certificate. Compare its SHA-256 fingerprint with this value before accepting:\n" + session.fingerprint)
            self.runner.submit(lambda: generate_qr(session.url), lambda result: self.show_qr(result) if serial == self.serial else None, self.failed)
            self.timer.start()
        self.runner.submit(lambda: ShareSession(host, data, kind, lifetime), complete, self.failed)

    def show_qr(self, result):
        if self.alive and self.session and not self.session.closed:
            self.image.setPixmap(QPixmap.fromImage(QImage.fromData(result[0])).scaledToHeight(260))

    def failed(self, message):
        if self.alive:
            self.message.setText(message)
            self.create.setEnabled(True)

    def tick(self):
        import time
        if self.session:
            remaining = max(0, int(self.session.deadline - time.monotonic()))
            self.message.setText(f"Available for {remaining} seconds · receive once" if self.session.data is not None and not self.session.closed else "Received, revoked, or expired.")
            if self.session.data is None or self.session.closed:
                self.url.clear()
                self.image.clear()

    def stop(self):
        self.serial += 1
        self.timer.stop()
        if self.session:
            self.session.close()
            self.session = None
        self.url.clear()
        self.image.clear()
        self.fingerprint.clear()
        self.create.setEnabled(self.host.count() > 0)
        self.message.setText("Transfer revoked. No clipboard contents are being served.")

    def done(self, result):
        self.alive = False
        self.stop()
        self.data = b""
        super().done(result)
