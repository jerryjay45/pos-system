"""
ui/login_window.py
Login screen — the first window shown when the POS system starts.
Uses plain QMainWindow (not BaseWindow) so it can be closed normally.
"""

import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QColor, QPalette, QKeyEvent


class LoginWindow(QMainWindow):
    """
    Login screen for the POS system.
    Authenticates the user and opens the correct dashboard based on their role.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("POS System — Login")
        self.setFixedSize(420, 520)
        self._center_on_screen()
        self._build_ui()

    # ----------------------------------------------------------------
    # UI CONSTRUCTION
    # ----------------------------------------------------------------

    def _build_ui(self):
        """Build and lay out all widgets on the login screen."""

        # Main container widget with dark background
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
            }
        """)
        self.setCentralWidget(container)

        # Outer layout — centres the card vertically
        outer_layout = QVBoxLayout(container)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer_layout.setContentsMargins(40, 40, 40, 40)

        # ── Login card ──────────────────────────────────────────────
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 16px;
                border: 1px solid #0f3460;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 40, 36, 40)
        card_layout.setSpacing(16)

        # ── Logo / title area ────────────────────────────────────────
        logo_label = QLabel("⬡")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("color: #e94560; font-size: 42px; border: none;")

        title_label = QLabel("POS System")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 2px;
            border: none;
        """)

        subtitle_label = QLabel("Sign in to continue")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            color: #8892a4;
            font-size: 13px;
            border: none;
            margin-bottom: 8px;
        """)

        # ── Username field ───────────────────────────────────────────
        username_label = QLabel("Username")
        username_label.setStyleSheet("color: #8892a4; font-size: 12px; border: none;")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(44)
        self.username_input.setStyleSheet(self._input_style())

        # ── Password field ───────────────────────────────────────────
        password_label = QLabel("Password")
        password_label.setStyleSheet("color: #8892a4; font-size: 12px; border: none;")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(44)
        self.password_input.setStyleSheet(self._input_style())

        # ── Error message label (hidden by default) ──────────────────
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("""
            color: #e94560;
            font-size: 12px;
            border: none;
            min-height: 18px;
        """)
        self.error_label.setVisible(False)

        # ── Login button ─────────────────────────────────────────────
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setFixedHeight(46)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet(self._button_style())
        self.login_btn.clicked.connect(self._handle_login)

        # ── Press Enter to log in ────────────────────────────────────
        self.password_input.returnPressed.connect(self._handle_login)
        self.username_input.returnPressed.connect(
            lambda: self.password_input.setFocus()
        )

        # ── Version label ────────────────────────────────────────────
        version_label = QLabel("v1.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #3a4555; font-size: 11px; border: none;")

        # ── Assemble card layout ─────────────────────────────────────
        card_layout.addWidget(logo_label)
        card_layout.addWidget(title_label)
        card_layout.addWidget(subtitle_label)
        card_layout.addWidget(username_label)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.error_label)
        card_layout.addWidget(self.login_btn)
        card_layout.addWidget(version_label)

        outer_layout.addWidget(card)

    # ----------------------------------------------------------------
    # LOGIN LOGIC
    # ----------------------------------------------------------------

    def _handle_login(self):
        """Called when the Sign In button is clicked or Enter is pressed."""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        # Basic validation — check fields are not empty
        if not username or not password:
            self._show_error("Please enter your username and password.")
            return

        # Attempt to authenticate against the database
        user = self._authenticate(username, password)

        if user is None:
            self._show_error("Invalid username or password.")
            self.password_input.clear()
            self.password_input.setFocus()
            return

        # Login successful — open the correct dashboard
        self._open_dashboard(user)

    def _authenticate(self, username, password):
        """
        Check the username and password against the database.
        Returns the user row if valid, None if not.
        """
        import hashlib
        from db import get_users_conn

        conn = get_users_conn()
        cursor = conn.cursor()

        # Hash the entered password to compare with stored hash
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute("""
            SELECT id, username, full_name, role
            FROM users
            WHERE username = ? AND password_hash = ? AND is_active = 1
        """, (username, password_hash))

        user = cursor.fetchone()
        conn.close()
        return user

    def _open_dashboard(self, user):
        """
        Open the correct dashboard based on the user's role.
        user = (id, username, full_name, role)
        """
        user_id, username, full_name, role = user

        # Close the login window
        self.close()

        # Open the appropriate dashboard
        if role == "cashier":
            from ui.cashier_dashboard import CashierDashboard
            self.dashboard = CashierDashboard(user_id, full_name)
        elif role == "supervisor":
            from ui.supervisor_dashboard import SupervisorDashboard
            self.dashboard = SupervisorDashboard(user_id, full_name)
        elif role == "manager":
            from ui.manager_dashboard import ManagerDashboard
            self.dashboard = ManagerDashboard(user_id, full_name)

        self.dashboard.show()

    # ----------------------------------------------------------------
    # HELPERS
    # ----------------------------------------------------------------

    def _show_error(self, message):
        """Show an error message below the password field."""
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def _center_on_screen(self):
        """Centre the window on the screen."""
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _input_style(self):
        return """
            QLineEdit {
                background-color: #0f3460;
                color: #ffffff;
                border: 1px solid #1a4a7a;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #e94560;
                background-color: #112244;
            }
            QLineEdit::placeholder {
                color: #3a5070;
            }
        """

    def _button_style(self):
        return """
            QPushButton {
                background-color: #e94560;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #ff5577;
            }
            QPushButton:pressed {
                background-color: #c73652;
            }
        """
