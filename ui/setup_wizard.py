"""
ui/setup_wizard.py
First-run setup wizard.
Shown automatically when no users exist in the database.
Creates the first manager account + sets business name and GCT rate.
Runs once and never shows again.
"""

import hashlib
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QMessageBox, QStackedWidget,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QDoubleValidator


# ── Step page base ────────────────────────────────────────────────────────────

class _StepPage(QWidget):
    """Base class for a wizard step."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(14)

    def validate(self):
        """Return (True, None) if OK, (False, error_message) if not."""
        return True, None

    def collect(self):
        """Return a dict of data from this step."""
        return {}


# ── Individual steps ──────────────────────────────────────────────────────────

class _WelcomePage(_StepPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        icon = QLabel("⬡")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("color: #f59e0b; font-size: 52px;")

        title = QLabel("Welcome to Merchant POS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #f0f6ff; font-size: 22px; font-weight: 700;")

        body = QLabel(
            "This looks like a fresh installation.\n"
            "Let's get you set up in just a few steps.\n\n"
            "You'll create your manager account and set\n"
            "your basic business information."
        )
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setWordWrap(True)
        body.setStyleSheet("color: #94aac4; font-size: 14px; line-height: 1.6;")

        self._layout.addStretch()
        self._layout.addWidget(icon)
        self._layout.addSpacing(6)
        self._layout.addWidget(title)
        self._layout.addSpacing(4)
        self._layout.addWidget(body)
        self._layout.addStretch()


class _AccountPage(_StepPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        title = QLabel("Create Manager Account")
        title.setStyleSheet("color: #f0f6ff; font-size: 18px; font-weight: 700;")

        subtitle = QLabel("This will be the primary administrator account.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #94aac4; font-size: 13px; margin-bottom: 6px;")

        self.f_fullname = self._inp("Full name", "e.g. John Smith")
        self.f_username = self._inp("Username", "e.g. admin")
        self.f_password = self._inp("Password", "Minimum 6 characters", echo=True)
        self.f_confirm  = self._inp("Confirm password", "", echo=True)

        self._layout.addWidget(title)
        self._layout.addWidget(subtitle)
        self._layout.addWidget(self._wrap("Full Name",        self.f_fullname))
        self._layout.addWidget(self._wrap("Username",         self.f_username))
        self._layout.addWidget(self._wrap("Password",         self.f_password))
        self._layout.addWidget(self._wrap("Confirm Password", self.f_confirm))
        self._layout.addStretch()

    def _inp(self, label, placeholder, echo=False):
        w = QLineEdit()
        w.setPlaceholderText(placeholder)
        w.setFixedHeight(38)
        if echo:
            w.setEchoMode(QLineEdit.EchoMode.Password)
        w.setStyleSheet(_INPUT_STYLE)
        return w

    def _wrap(self, label, widget):
        box = QWidget()
        box.setStyleSheet("background: transparent;")
        l = QVBoxLayout(box)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #5a7a9a; font-size: 11px; font-weight: 700; "
                          "text-transform: uppercase; letter-spacing: 0.5px;")
        l.addWidget(lbl)
        l.addWidget(widget)
        return box

    def validate(self):
        fname = self.f_fullname.text().strip()
        uname = self.f_username.text().strip()
        pw    = self.f_password.text()
        pw2   = self.f_confirm.text()
        if not fname:
            return False, "Please enter your full name."
        if not uname:
            return False, "Please enter a username."
        if len(uname) < 3:
            return False, "Username must be at least 3 characters."
        if len(pw) < 6:
            return False, "Password must be at least 6 characters."
        if pw != pw2:
            return False, "Passwords do not match."
        return True, None

    def collect(self):
        return {
            "full_name": self.f_fullname.text().strip(),
            "username":  self.f_username.text().strip(),
            "password":  self.f_password.text(),
        }


class _BusinessPage(_StepPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        title = QLabel("Business Information")
        title.setStyleSheet("color: #f0f6ff; font-size: 18px; font-weight: 700;")

        subtitle = QLabel(
            "You can change all of this later in the Manager dashboard."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #94aac4; font-size: 13px; margin-bottom: 6px;")

        self.f_name    = self._inp("Business name", "e.g. My Shop Ltd.")
        self.f_address = self._inp("Address (optional)", "e.g. 12 King St, Kingston")
        self.f_phone   = self._inp("Phone (optional)", "e.g. 876-555-0100")

        gct_row = QHBoxLayout()
        self.f_gct = QLineEdit()
        self.f_gct.setText("16.5")
        self.f_gct.setFixedHeight(38)
        self.f_gct.setFixedWidth(100)
        self.f_gct.setValidator(QDoubleValidator(0.0, 100.0, 2))
        self.f_gct.setStyleSheet(_INPUT_STYLE)
        pct_lbl = QLabel("%")
        pct_lbl.setStyleSheet("color: #94aac4; font-size: 15px;")
        gct_row.addWidget(self.f_gct)
        gct_row.addWidget(pct_lbl)
        gct_row.addStretch()

        gct_wrap = QWidget()
        gct_wrap.setStyleSheet("background: transparent;")
        gl = QVBoxLayout(gct_wrap)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(4)
        gct_title_lbl = QLabel("GCT Rate")
        gct_title_lbl.setStyleSheet("color: #5a7a9a; font-size: 11px; font-weight: 700; "
                                    "text-transform: uppercase; letter-spacing: 0.5px;")
        gl.addWidget(gct_title_lbl)
        gl.addLayout(gct_row)

        self._layout.addWidget(title)
        self._layout.addWidget(subtitle)
        self._layout.addWidget(self._wrap("Business Name", self.f_name))
        self._layout.addWidget(self._wrap("Address",       self.f_address))
        self._layout.addWidget(self._wrap("Phone",         self.f_phone))
        self._layout.addWidget(gct_wrap)
        self._layout.addStretch()

    def _inp(self, label, placeholder):
        w = QLineEdit()
        w.setPlaceholderText(placeholder)
        w.setFixedHeight(38)
        w.setStyleSheet(_INPUT_STYLE)
        return w

    def _wrap(self, label, widget):
        box = QWidget()
        box.setStyleSheet("background: transparent;")
        l = QVBoxLayout(box)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #5a7a9a; font-size: 11px; font-weight: 700; "
                          "text-transform: uppercase; letter-spacing: 0.5px;")
        l.addWidget(lbl)
        l.addWidget(widget)
        return box

    def validate(self):
        name = self.f_name.text().strip()
        if not name:
            return False, "Please enter your business name."
        try:
            gct = float(self.f_gct.text())
            if not (0 <= gct <= 100):
                raise ValueError
        except ValueError:
            return False, "GCT rate must be a number between 0 and 100."
        return True, None

    def collect(self):
        try:
            gct = float(self.f_gct.text())
        except ValueError:
            gct = 16.5
        return {
            "business_name": self.f_name.text().strip(),
            "address":       self.f_address.text().strip(),
            "phone":         self.f_phone.text().strip(),
            "gct":           gct,
        }


class _FinishPage(_StepPage):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.icon = QLabel("✓")
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setStyleSheet("color: #10d98a; font-size: 56px;")

        self.title = QLabel("All done!")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("color: #f0f6ff; font-size: 22px; font-weight: 700;")

        self.body = QLabel("")
        self.body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.setWordWrap(True)
        self.body.setStyleSheet("color: #94aac4; font-size: 14px; line-height: 1.6;")

        self._layout.addStretch()
        self._layout.addWidget(self.icon)
        self._layout.addSpacing(4)
        self._layout.addWidget(self.title)
        self._layout.addSpacing(4)
        self._layout.addWidget(self.body)
        self._layout.addStretch()

    def set_summary(self, username, business_name):
        self.body.setText(
            f"Manager account  \"{username}\"  created.\n"
            f"Business set to  \"{business_name}\".\n\n"
            "You'll be taken to the login screen now.\n"
            "Sign in with the credentials you just created."
        )


# ── Shared styles ─────────────────────────────────────────────────────────────

_INPUT_STYLE = """
    QLineEdit {
        background-color: #0d1e2e;
        color: #f0f6ff;
        border: 1.5px solid #1e3a5f;
        border-radius: 8px;
        padding: 0 14px;
        font-size: 14px;
    }
    QLineEdit:focus {
        border-color: #f59e0b;
        background-color: #172840;
    }
"""

_BTN_PRIMARY = """
    QPushButton {
        background-color: #f59e0b;
        color: #0a0400;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 700;
        padding: 0 24px;
    }
    QPushButton:hover   { background-color: #fbbf24; }
    QPushButton:pressed { background-color: #d97706; }
    QPushButton:disabled { background-color: #1e3a5f; color: #5a7a9a; }
"""

_BTN_OUTLINE = """
    QPushButton {
        background-color: transparent;
        color: #94aac4;
        border: 1.5px solid #1e3a5f;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        padding: 0 24px;
    }
    QPushButton:hover   { background-color: #172840; color: #f0f6ff; }
    QPushButton:pressed { background-color: #1e3a5f; }
    QPushButton:disabled { color: #2d4f6b; border-color: #0d1e2e; }
"""


# ── Main wizard window ────────────────────────────────────────────────────────

class SetupWizard(QMainWindow):
    """
    First-run setup wizard.
    Creates manager account + saves business info.
    On completion, opens LoginWindow.
    """

    def __init__(self, app=None):
        super().__init__()
        self._app = app
        self.setWindowTitle("Merchant POS — First Time Setup")
        self.setMinimumSize(460, 560)
        self.resize(480, 580)
        self._center_on_screen()
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet("QWidget { background-color: #07111f; }")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(28, 28, 28, 28)
        outer.setSpacing(16)

        # ── Progress dots ────────────────────────────────────────────
        self._dot_row = QHBoxLayout()
        self._dot_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dot_row.setSpacing(8)
        self._dots = []
        for _ in range(3):   # 3 data steps (welcome = 0, account = 1, business = 2, finish = 3)
            dot = QLabel("●")
            dot.setStyleSheet("color: #1e3a5f; font-size: 12px;")
            self._dot_row.addWidget(dot)
            self._dots.append(dot)
        outer.addLayout(self._dot_row)

        # ── Stacked pages ────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        self._page_welcome  = _WelcomePage()
        self._page_account  = _AccountPage()
        self._page_business = _BusinessPage()
        self._page_finish   = _FinishPage()

        self._stack.addWidget(self._page_welcome)   # 0
        self._stack.addWidget(self._page_account)   # 1
        self._stack.addWidget(self._page_business)  # 2
        self._stack.addWidget(self._page_finish)    # 3

        outer.addWidget(self._stack, stretch=1)

        # ── Error label ──────────────────────────────────────────────
        self._error_lbl = QLabel("")
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setStyleSheet(
            "color: #f87171; font-size: 12px; "
            "background: #2d0a0a; border-radius: 6px; padding: 6px 10px;"
        )
        self._error_lbl.hide()
        outer.addWidget(self._error_lbl)

        # ── Nav buttons ──────────────────────────────────────────────
        nav = QHBoxLayout()
        self._back_btn = QPushButton("← Back")
        self._back_btn.setFixedHeight(40)
        self._back_btn.setStyleSheet(_BTN_OUTLINE)
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self._go_back)

        self._next_btn = QPushButton("Get Started →")
        self._next_btn.setFixedHeight(40)
        self._next_btn.setStyleSheet(_BTN_PRIMARY)
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._go_next)

        nav.addWidget(self._back_btn)
        nav.addStretch()
        nav.addWidget(self._next_btn)
        outer.addLayout(nav)

        self._current = 0
        self._update_nav()

    # ── Navigation ─────────────────────────────────────────────────────

    def _go_next(self):
        page = self._stack.currentWidget()
        ok, err = page.validate()
        if not ok:
            self._show_error(err)
            return
        self._hide_error()

        if self._current == 3:
            # Finish — open login
            self._open_login()
            return

        self._current += 1
        self._stack.setCurrentIndex(self._current)

        if self._current == 3:
            self._save_data()

        self._update_nav()

    def _go_back(self):
        if self._current == 0:
            return
        self._current -= 1
        self._stack.setCurrentIndex(self._current)
        self._hide_error()
        self._update_nav()

    def _update_nav(self):
        idx = self._current
        # Back button
        self._back_btn.setEnabled(idx > 0 and idx < 3)
        self._back_btn.setVisible(idx > 0 and idx < 3)

        # Next / Finish button
        labels = {
            0: "Get Started →",
            1: "Next →",
            2: "Create Account →",
            3: "Go to Login →",
        }
        self._next_btn.setText(labels.get(idx, "Next →"))

        # Progress dots (steps 1 & 2 are the data steps)
        for i, dot in enumerate(self._dots):
            if i < idx:
                dot.setStyleSheet("color: #10d98a; font-size: 12px;")   # done
            elif i == idx - 1:
                dot.setStyleSheet("color: #f59e0b; font-size: 14px;")   # active
            else:
                dot.setStyleSheet("color: #1e3a5f; font-size: 12px;")   # future

    # ── Save ───────────────────────────────────────────────────────────

    def _save_data(self):
        acct = self._page_account.collect()
        biz  = self._page_business.collect()

        try:
            from db import get_users_conn, get_business_conn

            # Create manager user
            pw_hash = hashlib.sha256(acct["password"].encode()).hexdigest()
            uconn = get_users_conn()
            uconn.execute(
                "INSERT INTO users (username, password_hash, full_name, role, is_active) "
                "VALUES (?, ?, ?, 'manager', 1)",
                (acct["username"], pw_hash, acct["full_name"])
            )
            uconn.commit()
            uconn.close()

            # Save business info
            bconn = get_business_conn()
            bconn.execute("""
                UPDATE business_info
                SET business_name = ?,
                    address       = ?,
                    phone         = ?,
                    tax_percent   = ?
                WHERE id = 1
            """, (biz["business_name"], biz["address"], biz["phone"], biz["gct"]))
            bconn.commit()
            bconn.close()

            # Update finish page summary
            self._page_finish.set_summary(acct["username"], biz["business_name"])

        except Exception as e:
            self._show_error(f"Setup failed: {e}")
            self._current = 2
            self._stack.setCurrentIndex(2)
            self._update_nav()

    # ── Helpers ────────────────────────────────────────────────────────

    def _show_error(self, msg):
        self._error_lbl.setText(f"⚠  {msg}")
        self._error_lbl.show()

    def _hide_error(self):
        self._error_lbl.hide()
        self._error_lbl.setText("")

    def _open_login(self):
        self.close()
        from ui.login_window import LoginWindow
        self._login = LoginWindow(self._app)
        self._login.show()

    def _center_on_screen(self):
        screen = self.screen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

    def closeEvent(self, event):
        """Allow closing during setup (user may want to quit before finishing)."""
        reply = QMessageBox.question(
            self, "Quit Setup",
            "Setup is not complete. Are you sure you want to quit?\n"
            "The application will not work until setup is finished.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
            sys.exit(0)
        else:
            event.ignore()


# ── Helper: check if first run ────────────────────────────────────────────────

def is_first_run():
    """Return True if no users exist in the database."""
    try:
        from db import get_users_conn
        conn = get_users_conn()
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        return count == 0
    except Exception:
        return True
