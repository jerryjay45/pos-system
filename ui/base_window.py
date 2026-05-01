"""
ui/base_window.py
Base window class for all protected windows in the POS system.
Blocks the X button and shows a warning message instead.
All windows except the login screen should inherit from this class.

Usage:
    from ui.base_window import BaseWindow

    class MyWindow(BaseWindow):
        def __init__(self):
            super().__init__()
"""

from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QShortcut, QKeySequence


# Global zoom scale — persists across the session
_FONT_SCALE = 1.0
_BASE_FONT_SIZE = 13  # pts


class BaseWindow(QMainWindow):
    """
    A QMainWindow that blocks accidental closing via the X button.
    Shows a warning dialog instead, directing the user to use
    the logout/exit option from the menu or button.

    Zoom shortcuts (all windows):
        Ctrl++   Zoom in
        Ctrl+-   Zoom out
        Ctrl+0   Reset zoom
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_zoom_shortcuts()

    def _setup_zoom_shortcuts(self):
        """Attach Ctrl+Plus / Ctrl+Minus / Ctrl+0 for global zoom."""
        zoom_in  = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in2 = QShortcut(QKeySequence("Ctrl+="), self)  # Ctrl+= (no shift needed)
        zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_rst = QShortcut(QKeySequence("Ctrl+0"), self)
        zoom_in.activated.connect(lambda: self._zoom(+1))
        zoom_in2.activated.connect(lambda: self._zoom(+1))
        zoom_out.activated.connect(lambda: self._zoom(-1))
        zoom_rst.activated.connect(lambda: self._zoom(0))

    def _zoom(self, direction):
        """
        direction: +1 = larger, -1 = smaller, 0 = reset.
        Applies to the entire application via QApplication font scaling.
        """
        global _FONT_SCALE
        if direction == 0:
            _FONT_SCALE = 1.0
        elif direction > 0:
            _FONT_SCALE = min(_FONT_SCALE + 0.1, 2.0)
        else:
            _FONT_SCALE = max(_FONT_SCALE - 0.1, 0.6)

        new_size = max(8, round(_BASE_FONT_SIZE * _FONT_SCALE))
        app = QApplication.instance()
        if app:
            font = app.font()
            font.setPointSize(new_size)
            app.setFont(font)

        # Show feedback in the window title briefly
        pct = round(_FONT_SCALE * 100)
        orig_title = self.windowTitle()
        self.setWindowTitle(f"{orig_title}  [{pct}%]")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.setWindowTitle(orig_title))

    def closeEvent(self, event):
        """
        Called automatically by PyQt6 whenever the window is about to close.
        We override it here to block the X button and show a warning instead.
        """
        warning = QMessageBox(self)
        warning.setWindowTitle("Cannot Close")
        warning.setText("You cannot close this window using the X button.")
        warning.setInformativeText(
            "Please use the Logout or Exit option from the menu."
        )
        warning.setIcon(QMessageBox.Icon.Warning)
        warning.setStandardButtons(QMessageBox.StandardButton.Ok)
        warning.exec()

        # Ignore the close event — keeps the window open
        event.ignore()

    def force_close(self):
        """
        Call this method from your logout/exit button or menu item.
        This bypasses the closeEvent protection and actually closes the window.
        """
        self.closeEvent = lambda event: event.accept()
        self.close()
