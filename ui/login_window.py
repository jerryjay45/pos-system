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

    def __init__(self, app=None):
        super().__init__()
        self._app = app
        self.setWindowTitle("Merchant POS System — Login")
        self.setMinimumSize(380, 480)
        self.resize(420, 540)
        self._center_on_screen()
        self._build_ui()

    # ----------------------------------------------------------------
    # UI CONSTRUCTION
    # ----------------------------------------------------------------

    def _build_ui(self):
        """Build and lay out all widgets on the login screen."""

        # Main container widget with dark background
        container = QWidget()
        container.setStyleSheet("QWidget { background-color: #0b1120; }")
        self.setCentralWidget(container)

        # Outer layout — centres the card vertically
        outer_layout = QVBoxLayout(container)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer_layout.setContentsMargins(24, 24, 24, 24)

        # ── Login card ──────────────────────────────────────────────
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border-radius: 16px;
                border: 1.5px solid #1e3a5f;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 28, 24, 28)
        card_layout.setSpacing(12)

        # ── Logo / title area ────────────────────────────────────────
        logo_label = QLabel("⬡")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("color: #f59e0b; font-size: 48px; border: none;")

        title_label = QLabel("Merchant POS Systems")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            color: #f1f5f9;
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 1px;
            border: none;
        """)

        subtitle_label = QLabel("Sign in to continue")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            color: #64748b;
            font-size: 13px;
            border: none;
            margin-bottom: 8px;
        """)

        # ── Username field ───────────────────────────────────────────
        username_label = QLabel("Username")
        username_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600; border: none;")

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setMinimumHeight(38)
        self.username_input.setStyleSheet(self._input_style())

        # ── Password field ───────────────────────────────────────────
        password_label = QLabel("Password")
        password_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600; border: none;")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(38)
        self.password_input.setStyleSheet(self._input_style())

        # ── Error message label (hidden by default) ──────────────────

        # ── Login button ─────────────────────────────────────────────
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet(self._button_style())
        self.login_btn.clicked.connect(self._handle_login)

        # ── Press Enter to log in ────────────────────────────────────
        self.password_input.returnPressed.connect(self._handle_login)
        self.username_input.returnPressed.connect(
            lambda: self.password_input.setFocus()
        )

        # ── Version + theme toggle row ────────────────────────────────
        bottom_row = QHBoxLayout()
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet("color: #3a4555; font-size: 11px; border: none;")

        from ui.theme_toggle import ZoomWidget
        self._zoom_btn = ZoomWidget(self._app) if self._app else None

        bottom_row.addWidget(version_label)
        bottom_row.addStretch()
        if self._zoom_btn:
            bottom_row.addWidget(self._zoom_btn)

        # ── Assemble card layout ─────────────────────────────────────
        card_layout.addWidget(logo_label)
        card_layout.addWidget(title_label)
        card_layout.addWidget(subtitle_label)
        card_layout.addWidget(username_label)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.login_btn)
        card_layout.addLayout(bottom_row)

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
            QMessageBox.warning(self, "Missing Fields",
                                "Please enter your username and password.")
            return

        # Attempt to authenticate against the database
        user = self._authenticate(username, password)

        if user is None:
            QMessageBox.warning(self, "Login Failed",
                                "Invalid username or password.")
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

        # ── Gate: cashiers need an open cashing session ──────────────
        if role == "cashier":
            try:
                from db import get_transactions_conn
                conn = get_transactions_conn()
                row  = conn.execute(
                    "SELECT id FROM cashing_sessions "
                    "WHERE cashier_id = ? AND status = 'open' LIMIT 1",
                    (user_id,)
                ).fetchone()
                conn.close()
            except Exception:
                row = None

            if row is None:
                QMessageBox.warning(
                    self,
                    "No Session Open",
                    "Your account has no open session.\n"
                    "Please ask your supervisor to open one."
                )
                return

        # ── All clear — close login and open dashboard ────────────────
        self.close()

        if role == "cashier":
            from ui.cashier_dashboard import CashierDashboard
            self.dashboard = CashierDashboard(user_id, full_name, app=self._app)
        elif role == "supervisor":
            from ui.supervisor_dashboard import SupervisorDashboard
            self.dashboard = SupervisorDashboard(user_id, full_name, app=self._app)
        elif role == "manager":
            from ui.manager_dashboard import ManagerDashboard
            self.dashboard = ManagerDashboard(user_id, full_name, app=self._app)

        self.dashboard.show()

    # ----------------------------------------------------------------
    # HELPERS
    # ----------------------------------------------------------------

    def _center_on_screen(self):
        """Centre the window on the screen."""
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def _input_style(self):
        from ui.theme import ThemeManager
        v = ThemeManager.instance().palette
        return f"""
            QLineEdit {{
                background-color: {v['BG_INPUT']};
                color: {v['TEXT_PRIMARY']};
                border: 1.5px solid {v['BORDER']};
                border-radius: 8px;
                padding: 0 14px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {v['ACCENT']};
                background-color: {v['BG_ELEVATED']};
            }}
        """

    def _button_style(self):
        from ui.theme import ThemeManager
        v = ThemeManager.instance().palette
        return f"""
            QPushButton {{
                background-color: {v['ACCENT']};
                color: {v['ACCENT_TEXT']};
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            QPushButton:hover {{
                background-color: {v['ACCENT_HOVER']};
            }}
            QPushButton:pressed {{
                background-color: {v['ACCENT_PRESS']};
            }}
        """
