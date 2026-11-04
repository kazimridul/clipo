"""A restrained, accessible Qt Widgets theme."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication


def apply_theme(app, preference: str):
    dark = preference == "dark" or (
        preference == "system" and QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    )
    bg, panel, text, muted, line, hover = (
        ("#15161d", "#1e202a", "#eeedf6", "#aaaabd", "#343643", "#2b2d3b") if dark else
        ("#f6f6fa", "#ffffff", "#252435", "#6f7184", "#e3e3ee", "#eeedf8")
    )
    app.setStyleSheet(f"""
        QWidget {{ font-family: 'Inter', 'Noto Sans', 'DejaVu Sans'; font-size: 13px; color: {text}; }}
        QMainWindow, QDialog {{ background: {bg}; }}
        QFrame#sidebar {{ background: {panel}; border-right: 1px solid {line}; }}
        QLabel#brand {{ font-size: 25px; font-weight: 700; }}
        QLabel#heading {{ font-size: 24px; font-weight: 700; }}
        QLabel#muted, QLabel#metadata {{ color: {muted}; }}
        QLabel#eyebrow {{ color: {muted}; font-size: 11px; font-weight: 600; }}
        QLabel#notice {{ background: {hover}; padding: 10px; border-radius: 7px; color: {muted}; }}
        QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{ background: {panel}; border: 1px solid {line}; border-radius: 7px; padding: 9px; selection-background-color: #6754d9; }}
        QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid #8d7bea; }}
        QPushButton, QToolButton {{ background: {panel}; border: 1px solid {line}; border-radius: 7px; padding: 9px 13px; }}
        QPushButton:hover, QToolButton:hover {{ background: {hover}; }}
        QToolButton::menu-indicator {{ width: 0; }}
        QComboBox::drop-down {{ border: 0; width: 22px; }}
        QComboBox QAbstractItemView {{ background: {panel}; color: {text}; selection-background-color: {hover}; selection-color: {text}; }}
        QTabWidget::pane {{ border: 1px solid {line}; background: {panel}; }}
        QTabBar::tab {{ background: {bg}; padding: 10px; border-bottom: 2px solid transparent; }}
        QTabBar::tab:selected {{ background: {panel}; border-bottom: 2px solid #8d7bea; }}
        QPushButton:pressed {{ background: #6754d9; color: white; }}
        QPushButton:disabled {{ color: {muted}; }}
        QPushButton#primary {{ background: #6754d9; color: white; border: 0; font-weight: 600; }}
        QPushButton#primary:hover {{ background: #7866e3; }}
        QPushButton#nav {{ text-align: left; border: 0; padding: 11px 14px; }}
        QPushButton#nav:checked {{ background: {hover}; color: #8b73e8; font-weight: 600; }}
        QListWidget {{ background: transparent; border: 0; outline: 0; }}
        QListWidget::item {{ background: {panel}; border: 1px solid {line}; border-radius: 9px; padding: 13px; margin-bottom: 9px; }}
        QListWidget::item:hover {{ background: {hover}; }}
        QListWidget::item:selected {{ background: {hover}; color: {text}; border: 1px solid #8d7bea; }}
        QScrollBar:vertical {{ background: transparent; width: 8px; }}
        QScrollBar::handle:vertical {{ background: {line}; border-radius: 4px; min-height: 30px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QSplitter::handle {{ background: {line}; width: 1px; }}
        QStatusBar {{ background: {panel}; color: {muted}; border-top: 1px solid {line}; }}
        QMenu {{ background: {panel}; border: 1px solid {line}; padding: 5px; }}
        QMenu::item {{ padding: 7px 20px; }}
        QMenu::item:selected {{ background: {hover}; }}
        QToolTip {{ background: {panel}; color: {text}; border: 1px solid {line}; }}
    """)

