"""Native history cards with a keyboard-accessible QR action at their right edge."""
from PySide6.QtCore import QTimer, QSize, Qt, QRect
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import QListWidget, QStyledItemDelegate, QStyle, QStyleOptionViewItem, QToolButton
from pathlib import Path


class HistoryDelegate(QStyledItemDelegate):
    """Reserve room for the button while preserving native card/thumbnail painting."""

    def paint(self, painter, option, index):
        painter.save()
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        style = option.widget.style()
        # Match the card's 13px padding, 1px border and 9px bottom gap.
        text_rect = option.rect.adjusted(14, 14, -58, -23)
        icon = QIcon(option.icon)
        if not icon.isNull():
            size = icon.actualSize(QSize(72, 54))
            icon_rect = QRect(text_rect.left(), text_rect.top() + (text_rect.height() - size.height()) // 2, size.width(), size.height())
            text_rect.setLeft(text_rect.left() + size.width() + 8)
        text = "\n".join(option.fontMetrics.elidedText(line, Qt.TextElideMode.ElideRight, max(0, text_rect.width())) for line in option.text.splitlines())
        option.text = ""
        option.icon = QIcon()
        painter.save()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, option, painter, option.widget)
        painter.restore()
        if not icon.isNull():
            icon.paint(painter, icon_rect)
        painter.setFont(option.font)
        painter.setPen(option.palette.color(QPalette.ColorRole.Text))
        painter.setClipRect(text_rect)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignVCenter, text)
        painter.restore()


class HistoryList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(HistoryDelegate(self))
        self._qr_buttons = []
        self._layout_timer = QTimer(self)
        self._layout_timer.setSingleShot(True)
        self._layout_timer.timeout.connect(self.position_actions)
        self._qr_icon = QIcon(str(Path(__file__).parents[1] / "resources/qr.svg"))

    def add_qr_action(self, entry, item_id, callback, enabled=True):
        button = QToolButton(self.viewport())
        button.setObjectName("rowQr")
        button.setIcon(self._qr_icon)
        button.setIconSize(QSize(20, 20))
        button.setFixedSize(34, 34)
        button.setAccessibleName("Generate QR code")
        button.setAccessibleDescription("Share this item's text as a QR code")
        button.setToolTip("Generate QR code to share this text" if enabled else "Extract text from this image first to generate a QR code")
        button.setEnabled(enabled)
        button.clicked.connect(lambda checked=False: callback(item_id))
        self._qr_buttons.append((entry, button))
        self._layout_timer.start(0)

    def clear(self):
        self._layout_timer.stop()
        for _, button in self._qr_buttons:
            button.hide()
            button.deleteLater()
        self._qr_buttons.clear()
        super().clear()

    def position_actions(self):
        viewport = self.viewport().rect()
        for entry, button in self._qr_buttons:
            rect = self.visualItemRect(entry)
            visible = rect.intersects(viewport) and rect.width() > 60
            if visible:
                button.move(rect.right() - button.width() - 13, rect.top() + max(0, (rect.height() - 9 - button.height()) // 2))
            button.setVisible(visible)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_layout_timer"):
            self._layout_timer.start(0)

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.position_actions()
