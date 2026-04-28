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

from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6.QtCore import Qt


class BaseWindow(QMainWindow):
    """
    A QMainWindow that blocks accidental closing via the X button.
    Shows a warning dialog instead, directing the user to use
    the logout/exit option from the menu or button.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def closeEvent(self, event):
        """
        Called automatically by PyQt6 whenever the window is about to close.
        We override it here to block the X button and show a warning instead.
        """
        # Show a warning message box
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
        # Temporarily allow closing, then close
        self.closeEvent = lambda event: event.accept()
        self.close()
