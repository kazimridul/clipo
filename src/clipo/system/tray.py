from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class Tray(QSystemTrayIcon):
    def __init__(self, icon, window, quit_callback):
        super().__init__(icon, window)
        self.setToolTip("Clipo · clipboard history")
        menu = QMenu(window)
        menu.addAction("Open Clipo", lambda: self.reveal(window))
        menu.addAction("Quick clipboard", lambda: window.operation_requested.emit("quick", None))
        menu.addAction("Generate QR", lambda: window.operation_requested.emit("manual_qr", None))
        self.pause = menu.addAction("Pause capture")
        self.pause.setCheckable(True)
        self.pause.toggled.connect(window.pause_button.setChecked)
        window.pause_button.toggled.connect(self.pause.setChecked)
        self.private = menu.addAction("Private mode")
        self.private.setCheckable(True)
        self.private.toggled.connect(window.private_button.setChecked)
        window.private_button.toggled.connect(self.private.setChecked)
        menu.addAction("Settings", window.settings_requested.emit)
        menu.addSeparator()
        menu.addAction("Quit Clipo", quit_callback)
        self.setContextMenu(menu)
        self.activated.connect(lambda reason: self.reveal(window) if reason == QSystemTrayIcon.ActivationReason.Trigger else None)

    @staticmethod
    def reveal(window):
        window.showNormal()
        window.raise_()
        window.activateWindow()

