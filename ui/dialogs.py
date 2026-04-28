"""
ui/dialogs.py
Shared dialogs — stubs for now, will be built later.
"""
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt


class VoidDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Void Transaction")
        self.setMinimumSize(300, 200)
        layout = QVBoxLayout(self)
        label = QLabel("Void — Coming soon!")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
