"""
ui/manager_dashboard.py
Manager dashboard — stub for now, will be built later.
"""
from ui.base_window import BaseWindow
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt


class ManagerDashboard(BaseWindow):
    def __init__(self, user_id, full_name):
        super().__init__()
        self.user_id   = user_id
        self.full_name = full_name
        self.setWindowTitle("POS System — Manager")
        self.setMinimumSize(1280, 680)

        root = QWidget()
        root.setStyleSheet("background-color: #1a1a2e;")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        label = QLabel(f"Manager Dashboard\nComing soon — {full_name}")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #ffffff; font-size: 20px;")
        layout.addWidget(label)
