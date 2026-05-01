"""
ui/manager_dashboard.py
Manager dashboard.

Inherits the full SupervisorDashboard (Products, Reports, Transactions,
Void / Refund) and adds manager-only tabs:
  • Users       — add / edit / deactivate users, role assignment
  • Business    — business info, GCT %, discount levels, product groups
"""

import hashlib
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QAbstractItemView,
    QMessageBox, QFormLayout, QScrollArea, QCheckBox,
    QDoubleSpinBox, QSpinBox, QSizePolicy, QSplitter,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QDoubleValidator

from ui.supervisor_dashboard import SupervisorDashboard
from db import get_users_conn, get_business_conn, get_products_conn


# ──────────────────────────────────────────────────────────────────────────────
# SHARED STYLE CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

_BTN_BLUE = """
    QPushButton {
        background-color: #1a56db; color: #ffffff;
        border: none; border-radius: 8px;
        font-size: 13px; font-weight: 600; padding: 0 18px;
    }
    QPushButton:hover  { background-color: #1145b0; }
    QPushButton:pressed{ background-color: #0e3a8a; }
    QPushButton:disabled{ background-color: #1a2540; color: #4a5a7a; }
"""
_BTN_RED = """
    QPushButton {
        background: #7f1d1d; color: #fca5a5;
        border: none; border-radius: 8px;
        font-size: 12px; font-weight: 600; padding: 0 14px;
    }
    QPushButton:hover  { background: #991b1b; }
    QPushButton:pressed{ background: #b91c1c; }
    QPushButton:disabled{ background: #2d1515; color: #6b3030; }
"""
_BTN_GREEN = """
    QPushButton {
        background: #14532d; color: #86efac;
        border: none; border-radius: 8px;
        font-size: 12px; font-weight: 600; padding: 0 14px;
    }
    QPushButton:hover  { background: #166534; }
    QPushButton:pressed{ background: #15803d; }
    QPushButton:disabled{ background: #0d2b18; color: #3a6b4a; }
"""
_BTN_OUTLINE = """
    QPushButton {
        background: transparent; color: #c9d1d9;
        border: 1.5px solid #30363d; border-radius: 8px;
        font-size: 12px; font-weight: 600; padding: 0 14px;
    }
    QPushButton:hover  { background: #21262d; color: #ffffff; }
    QPushButton:pressed{ background: #30363d; }
    QPushButton:disabled{ color: #3d444d; border-color: #21262d; }
"""
_INPUT = """
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
        background-color: #0d1117; color: #ffffff;
        border: 1.5px solid #30363d; border-radius: 8px;
        padding: 0 12px; font-size: 13px;
    }
    QLineEdit:focus, QComboBox:focus,
    QDoubleSpinBox:focus, QSpinBox:focus { border-color: #1a56db; }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox QAbstractItemView {
        background: #0d1117; color: #c9d1d9;
        border: 1px solid #30363d; selection-background-color: #1a56db;
    }
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
    QSpinBox::up-button, QSpinBox::down-button {
        background: #21262d; border: none; width: 18px;
    }
"""
_TABLE = """
    QTableWidget { background: transparent; color: #c9d1d9; border: none; font-size: 12px; }
    QTableWidget::item { padding: 8px; border-bottom: 1px solid #21262d; }
    QTableWidget::item:selected { background-color: #1a56db22; color: #ffffff; }
    QHeaderView::section { background: #0d1117; color: #8b949e; border: none; padding: 8px;
                           font-size: 11px; font-weight: 700; border-bottom: 1px solid #21262d; }
"""
_SECTION_LBL = "color: #8b949e; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
_DIVIDER     = "background: #30363d;"


# ──────────────────────────────────────────────────────────────────────────────
# LIVE-SEARCH WIDGET  (used by Quick Keys tab)
# ──────────────────────────────────────────────────────────────────────────────

class _ProductSearchWidget(QWidget):
    """
    Google-search-style product picker.
    Type to filter → results drop down inline → click to confirm.
    Call currentData() to get the selected product ID (None = unassigned).
    """

    _INPUT_STYLE = """
        QLineEdit {
            background-color: #0d1117; color: #ffffff;
            border: 1.5px solid #30363d; border-radius: 8px;
            padding: 0 12px; font-size: 13px;
        }
        QLineEdit:focus { border-color: #1a56db; }
    """
    _LIST_STYLE = """
        QListWidget {
            background-color: #161b22; color: #c9d1d9;
            border: 1.5px solid #1a56db; border-radius: 0 0 8px 8px;
            border-top: none; font-size: 12px;
        }
        QListWidget::item { padding: 7px 12px; border-bottom: 1px solid #21262d; }
        QListWidget::item:selected { background-color: #1a56db; color: #ffffff; }
        QListWidget::item:hover    { background-color: #21262d; }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_pid  = None
        self._all_products  = []   # list of (id, name, price)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.search_input = QLineEdit()
        self.search_input.setFixedHeight(34)
        self.search_input.setPlaceholderText("Search products…")
        self.search_input.setStyleSheet(self._INPUT_STYLE)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.installEventFilter(self)

        self.results_list = QListWidget()
        self.results_list.setVisible(False)
        self.results_list.setMaximumHeight(168)   # 5 rows × ~33px
        self.results_list.setStyleSheet(self._LIST_STYLE)
        self.results_list.itemClicked.connect(self._on_item_clicked)
        self.results_list.installEventFilter(self)

        layout.addWidget(self.search_input)
        layout.addWidget(self.results_list)

    # ── Public API ────────────────────────────────────────────────────

    def set_products(self, products):
        """Load the full product list: [(id, name, price), …]."""
        self._all_products = products

    def set_selection(self, pid, display_text):
        """Pre-select a product by ID (loading saved assignment)."""
        self._selected_pid = pid
        self.search_input.blockSignals(True)
        self.search_input.setText(display_text)
        self.search_input.blockSignals(False)
        self.results_list.setVisible(False)

    def clear_selection(self):
        self._selected_pid = None
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self.results_list.setVisible(False)

    def currentData(self):
        """Return selected product ID, or None."""
        return self._selected_pid

    # ── Internal logic ────────────────────────────────────────────────

    def _on_text_changed(self, text):
        self._selected_pid = None   # typing clears the confirmed selection
        q = text.strip().lower()
        if not q:
            self.results_list.setVisible(False)
            return
        matches = [
            (pid, name, price)
            for pid, name, price in self._all_products
            if q in name.lower()
        ][:10]
        self.results_list.clear()
        if matches:
            for pid, name, price in matches:
                item = QListWidgetItem(f"{name}  —  ${price:.2f}")
                item.setData(Qt.ItemDataRole.UserRole, (pid, f"{name}  (${price:.2f})"))
                self.results_list.addItem(item)
            self.results_list.setVisible(True)
        else:
            no = QListWidgetItem("  No products found")
            no.setForeground(QColor("#484f58"))
            no.setFlags(no.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.results_list.addItem(no)
            self.results_list.setVisible(True)

    def _on_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        pid, display = data
        self._selected_pid = pid
        self.search_input.blockSignals(True)
        self.search_input.setText(display)
        self.search_input.blockSignals(False)
        self.results_list.setVisible(False)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        # Down arrow in search_input → move focus to list
        if obj is self.search_input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Down and self.results_list.isVisible():
                self.results_list.setCurrentRow(0)
                self.results_list.setFocus()
                return True
            if event.key() == Qt.Key.Key_Escape:
                self.results_list.setVisible(False)
                return True
        # Enter/Up in results_list
        if obj is self.results_list and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                cur = self.results_list.currentItem()
                if cur:
                    self._on_item_clicked(cur)
                return True
            if event.key() == Qt.Key.Key_Up and self.results_list.currentRow() == 0:
                self.search_input.setFocus()
                return True
        return super().eventFilter(obj, event)


# ──────────────────────────────────────────────────────────────────────────────
# MANAGER DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────

class ManagerDashboard(SupervisorDashboard):
    """
    Extends SupervisorDashboard.
    Supervisor tabs (Products, Reports, Transactions, Void/Refund) are
    inherited as-is.  Manager-only tabs are prepended.
    """

    def __init__(self, user_id, full_name):
        # Call grandparent __init__ (BaseWindow) directly so we control
        # everything ourselves, then replicate SupervisorDashboard setup.
        super().__init__(user_id, full_name, role="manager")

    # ── Override window title & tab order ────────────────────────────

    def _build_ui(self):
        """Override to inject manager tabs first."""
        from PyQt6.QtWidgets import QVBoxLayout, QWidget
        root = QWidget()
        root.setStyleSheet("background-color: #0d1117;")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(self._build_topbar())
        layout.addWidget(self._build_tabs(), stretch=1)

        self.setWindowTitle("POS System — Manager")
        self.setMinimumSize(1280, 720)
        self._center_on_screen()

    def _build_topbar(self):
        bar = QFrame()
        bar.setFixedHeight(52)
        # Manager gets a teal/darker topbar to distinguish from supervisor
        bar.setStyleSheet("background-color: #0f766e; border-radius: 10px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        left = QLabel(f"POS System  |  Manager:  {self.full_name}")
        left.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600;")

        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_label.setStyleSheet("color: #ffffff; font-size: 14px;")

        logout_btn = QPushButton("Logout  ↗")
        logout_btn.setFixedSize(120, 36)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #111827; color: #ffffff;
                border: none; border-radius: 18px;
                font-size: 13px; font-weight: 700;
            }
            QPushButton:hover   { background-color: #1f2937; }
            QPushButton:pressed { background-color: #374151; }
        """)
        logout_btn.clicked.connect(self._handle_logout)

        layout.addWidget(left)
        layout.addStretch()
        layout.addWidget(self.clock_label)
        layout.addStretch()
        layout.addWidget(logout_btn)
        return bar

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #161b22;
                border: none;
                border-radius: 0 8px 8px 8px;
            }
            QTabBar::tab {
                background-color: #21262d;
                color: #8b949e;
                border: 1px solid #30363d;
                border-bottom: none;
                border-radius: 6px 6px 0 0;
                padding: 8px 20px;
                font-size: 13px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #161b22;
                color: #ffffff;
                font-weight: 700;
            }
            QTabBar::tab:hover { background-color: #30363d; color: #ffffff; }
        """)

        # Manager-only tabs first
        self.tabs.addTab(self._build_users_tab(),      "👥  Users")
        self.tabs.addTab(self._build_business_tab(),   "🏢  Business")
        self.tabs.addTab(self._build_quickkeys_tab(),  "⌨  Quick Keys")
        self.tabs.addTab(self._build_sync_tab(),       "🔄  PostgreSQL")

        # Inherited supervisor tabs
        self.tabs.addTab(self._build_products_tab(),     "Products")
        self.tabs.addTab(self._build_reports_tab(),      "Reports")
        self.tabs.addTab(self._build_transactions_tab(), "Transactions")
        self.tabs.addTab(self._build_void_tab(),         "Void / Refund")

        self.tabs.setCurrentIndex(0)
        return self.tabs

    # ================================================================
    # USERS TAB
    # ================================================================

    def _build_users_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── Left: user list ──────────────────────────────────────────
        left = QFrame()
        left.setStyleSheet("background: #0d1117; border-radius: 8px;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 10, 10)
        ll.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        self.usr_search = QLineEdit()
        self.usr_search.setPlaceholderText("🔍  Search users…")
        self.usr_search.setFixedHeight(36)
        self.usr_search.setStyleSheet(_INPUT + "QLineEdit { border-radius: 18px; padding: 0 16px; }")
        self.usr_search.textChanged.connect(self._usr_filter)

        self.usr_role_filter = QComboBox()
        self.usr_role_filter.addItems(["All Roles", "Cashier", "Supervisor", "Manager"])
        self.usr_role_filter.setFixedHeight(36)
        self.usr_role_filter.setFixedWidth(130)
        self.usr_role_filter.setStyleSheet(_INPUT + "QComboBox { border-radius: 18px; }")
        self.usr_role_filter.currentIndexChanged.connect(self._usr_filter)

        add_usr_btn = QPushButton("+ Add User")
        add_usr_btn.setFixedHeight(36)
        add_usr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_usr_btn.setStyleSheet(_BTN_BLUE + "QPushButton { border-radius: 18px; padding: 0 16px; }")
        add_usr_btn.clicked.connect(self._usr_new_form)

        toolbar.addWidget(self.usr_search, stretch=1)
        toolbar.addWidget(self.usr_role_filter)
        toolbar.addWidget(add_usr_btn)
        ll.addLayout(toolbar)

        # User table
        self.usr_table = QTableWidget()
        self.usr_table.setColumnCount(5)
        self.usr_table.setHorizontalHeaderLabels(["Name", "Username", "Role", "Status", "Actions"])
        self.usr_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.usr_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.usr_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.usr_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.usr_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.usr_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.usr_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.usr_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.usr_table.verticalHeader().setVisible(False)
        self.usr_table.setShowGrid(False)
        self.usr_table.setStyleSheet(_TABLE)
        self.usr_table.selectionModel().selectionChanged.connect(self._usr_on_row_selected)
        ll.addWidget(self.usr_table, stretch=1)

        # ── Right: user form ─────────────────────────────────────────
        right = QFrame()
        right.setFixedWidth(320)
        right.setStyleSheet("background: #0d1117; border-radius: 8px;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 16, 16, 16)
        rl.setSpacing(10)

        self.usr_form_title = QLabel("Add User")
        self.usr_form_title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 700;")
        rl.addWidget(self.usr_form_title)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(_DIVIDER)
        rl.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        lbl_style = "color: #8b949e; font-size: 12px;"

        self.usr_f_fullname = QLineEdit()
        self.usr_f_fullname.setFixedHeight(34)
        self.usr_f_fullname.setStyleSheet(_INPUT)
        self.usr_f_fullname.setPlaceholderText("Full name")

        self.usr_f_username = QLineEdit()
        self.usr_f_username.setFixedHeight(34)
        self.usr_f_username.setStyleSheet(_INPUT)
        self.usr_f_username.setPlaceholderText("Login username")

        self.usr_f_password = QLineEdit()
        self.usr_f_password.setFixedHeight(34)
        self.usr_f_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.usr_f_password.setStyleSheet(_INPUT)
        self.usr_f_password.setPlaceholderText("Password (leave blank to keep)")

        self.usr_f_role = QComboBox()
        self.usr_f_role.addItems(["cashier", "supervisor", "manager"])
        self.usr_f_role.setFixedHeight(34)
        self.usr_f_role.setStyleSheet(_INPUT)

        self.usr_f_active = QCheckBox("Active")
        self.usr_f_active.setChecked(True)
        self.usr_f_active.setStyleSheet("color: #c9d1d9; font-size: 13px;")

        for lbl_text, widget in [
            ("Full Name", self.usr_f_fullname),
            ("Username",  self.usr_f_username),
            ("Password",  self.usr_f_password),
            ("Role",      self.usr_f_role),
            ("",          self.usr_f_active),
        ]:
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet(lbl_style)
            form.addRow(lbl, widget)

        rl.addLayout(form)
        rl.addStretch()

        # Feedback label
        self.usr_feedback = QLabel("")
        self.usr_feedback.setStyleSheet("color: #3dd68c; font-size: 11px; font-weight: 600;")
        self.usr_feedback.setWordWrap(True)
        self.usr_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(self.usr_feedback)

        # Action buttons
        btn_row = QHBoxLayout()
        self.usr_save_btn = QPushButton("💾  Save")
        self.usr_save_btn.setFixedHeight(36)
        self.usr_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.usr_save_btn.setStyleSheet(_BTN_BLUE)
        self.usr_save_btn.clicked.connect(self._usr_save)

        self.usr_delete_btn = QPushButton("🗑  Delete")
        self.usr_delete_btn.setFixedHeight(36)
        self.usr_delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.usr_delete_btn.setStyleSheet(_BTN_RED)
        self.usr_delete_btn.setEnabled(False)
        self.usr_delete_btn.clicked.connect(self._usr_delete)

        self.usr_clear_btn = QPushButton("Clear")
        self.usr_clear_btn.setFixedHeight(36)
        self.usr_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.usr_clear_btn.setStyleSheet(_BTN_OUTLINE)
        self.usr_clear_btn.clicked.connect(self._usr_new_form)

        btn_row.addWidget(self.usr_save_btn, stretch=1)
        btn_row.addWidget(self.usr_delete_btn)
        btn_row.addWidget(self.usr_clear_btn)
        rl.addLayout(btn_row)

        layout.addWidget(left, stretch=1)
        layout.addWidget(right)

        # Internal state
        self._usr_editing_id  = None
        self._usr_all_users   = []

        self._usr_load()
        return w

    # ── Users: data & logic ───────────────────────────────────────────

    def _usr_load(self):
        try:
            conn = get_users_conn()
            rows = conn.execute(
                "SELECT id, full_name, username, role, is_active FROM users ORDER BY full_name"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        self._usr_all_users = [
            {"id": r[0], "full_name": r[1], "username": r[2],
             "role": r[3], "is_active": r[4]}
            for r in rows
        ]
        self._usr_populate(self._usr_all_users)

    def _usr_populate(self, users):
        tbl = self.usr_table
        tbl.setRowCount(0)
        role_colors = {"cashier": "#60a5fa", "supervisor": "#fcd34d", "manager": "#f87171"}
        for u in users:
            row = tbl.rowCount()
            tbl.insertRow(row)

            name_item = QTableWidgetItem(u["full_name"])
            name_item.setData(Qt.ItemDataRole.UserRole, u["id"])
            name_item.setForeground(QColor("#ffffff"))

            user_item   = QTableWidgetItem(u["username"])
            role_item   = QTableWidgetItem(u["role"].capitalize())
            role_item.setForeground(QColor(role_colors.get(u["role"], "#c9d1d9")))
            role_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            status_text = "Active" if u["is_active"] else "Inactive"
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor("#3dd68c" if u["is_active"] else "#f87171"))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Edit button cell
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedHeight(26)
            edit_btn.setStyleSheet(_BTN_OUTLINE + "QPushButton { font-size: 11px; border-radius: 5px; }")
            edit_btn.clicked.connect(lambda _, uid=u["id"]: self._usr_load_form(uid))
            edit_cell = QWidget()
            eh = QHBoxLayout(edit_cell)
            eh.addWidget(edit_btn); eh.setContentsMargins(4, 2, 4, 2)

            for col, item in enumerate([name_item, user_item, role_item, status_item]):
                tbl.setItem(row, col, item)
            tbl.setCellWidget(row, 4, edit_cell)
        tbl.resizeRowsToContents()

    def _usr_filter(self):
        q    = self.usr_search.text().lower()
        role = self.usr_role_filter.currentText().lower()
        filtered = [
            u for u in self._usr_all_users
            if (q in u["full_name"].lower() or q in u["username"].lower())
            and (role == "all roles" or u["role"] == role)
        ]
        self._usr_populate(filtered)

    def _usr_on_row_selected(self):
        row = self.usr_table.currentRow()
        item = self.usr_table.item(row, 0)
        if item:
            self._usr_load_form(item.data(Qt.ItemDataRole.UserRole))

    def _usr_load_form(self, user_id):
        u = next((u for u in self._usr_all_users if u["id"] == user_id), None)
        if not u:
            return
        self._usr_editing_id = user_id
        self.usr_form_title.setText(f"Edit: {u['full_name']}")
        self.usr_f_fullname.setText(u["full_name"])
        self.usr_f_username.setText(u["username"])
        self.usr_f_password.clear()
        idx = self.usr_f_role.findText(u["role"])
        if idx >= 0:
            self.usr_f_role.setCurrentIndex(idx)
        self.usr_f_active.setChecked(bool(u["is_active"]))
        self.usr_delete_btn.setEnabled(user_id != self.user_id)  # can't delete yourself
        self.usr_feedback.setText("")

    def _usr_new_form(self):
        self._usr_editing_id = None
        self.usr_form_title.setText("Add User")
        self.usr_f_fullname.clear()
        self.usr_f_username.clear()
        self.usr_f_password.clear()
        self.usr_f_role.setCurrentIndex(0)
        self.usr_f_active.setChecked(True)
        self.usr_delete_btn.setEnabled(False)
        self.usr_feedback.setText("")
        self.usr_table.clearSelection()

    def _usr_save(self):
        full_name = self.usr_f_fullname.text().strip()
        username  = self.usr_f_username.text().strip()
        password  = self.usr_f_password.text()
        role      = self.usr_f_role.currentText()
        is_active = 1 if self.usr_f_active.isChecked() else 0

        if not full_name or not username:
            self.usr_feedback.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 600;")
            self.usr_feedback.setText("Full name and username are required.")
            return
        if self._usr_editing_id is None and not password:
            self.usr_feedback.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 600;")
            self.usr_feedback.setText("Password required for new user.")
            return

        try:
            conn = get_users_conn()
            if self._usr_editing_id is None:
                ph = hashlib.sha256(password.encode()).hexdigest()
                conn.execute(
                    "INSERT INTO users (username, password_hash, full_name, role, is_active) VALUES (?,?,?,?,?)",
                    (username, ph, full_name, role, is_active)
                )
                msg = f"User '{full_name}' created."
            else:
                if password:
                    ph = hashlib.sha256(password.encode()).hexdigest()
                    conn.execute(
                        "UPDATE users SET full_name=?, username=?, password_hash=?, role=?, is_active=? WHERE id=?",
                        (full_name, username, ph, role, is_active, self._usr_editing_id)
                    )
                else:
                    conn.execute(
                        "UPDATE users SET full_name=?, username=?, role=?, is_active=? WHERE id=?",
                        (full_name, username, role, is_active, self._usr_editing_id)
                    )
                msg = f"User '{full_name}' updated."
            conn.commit()
            conn.close()
            self.usr_feedback.setStyleSheet("color: #3dd68c; font-size: 11px; font-weight: 600;")
            self.usr_feedback.setText(msg)
            self._usr_load()
            self._usr_new_form()
        except Exception as e:
            self.usr_feedback.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 600;")
            self.usr_feedback.setText(str(e))

    def _usr_delete(self):
        if not self._usr_editing_id or self._usr_editing_id == self.user_id:
            return
        u = next((u for u in self._usr_all_users if u["id"] == self._usr_editing_id), None)
        name = u["full_name"] if u else f"#{self._usr_editing_id}"
        reply = QMessageBox.question(
            self, "Delete User",
            f"Delete user '{name}'?\n\nTransaction history will not be affected.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            conn = get_users_conn()
            conn.execute("DELETE FROM users WHERE id=?", (self._usr_editing_id,))
            conn.commit()
            conn.close()
            self._usr_load()
            self._usr_new_form()
        except Exception as e:
            QMessageBox.critical(self, "Delete Failed", str(e))

    # ================================================================
    # BUSINESS TAB
    # ================================================================

    def _build_business_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        main = QHBoxLayout(w)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)

        main.addWidget(self._build_biz_info_panel(), stretch=1)
        main.addWidget(self._build_biz_settings_panel(), stretch=1)
        return w

    # ── Business info panel ───────────────────────────────────────────

    def _build_biz_info_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background: #0d1117; border-radius: 8px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("BUSINESS INFORMATION")
        title.setStyleSheet(_SECTION_LBL)
        layout.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(_DIVIDER)
        layout.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_s = "color: #8b949e; font-size: 12px;"

        self.biz_name    = QLineEdit(); self.biz_name.setFixedHeight(34); self.biz_name.setStyleSheet(_INPUT); self.biz_name.setPlaceholderText("Business name")
        self.biz_address = QLineEdit(); self.biz_address.setFixedHeight(34); self.biz_address.setStyleSheet(_INPUT); self.biz_address.setPlaceholderText("Address")
        self.biz_phone   = QLineEdit(); self.biz_phone.setFixedHeight(34); self.biz_phone.setStyleSheet(_INPUT); self.biz_phone.setPlaceholderText("Phone")
        self.biz_footer  = QLineEdit(); self.biz_footer.setFixedHeight(34); self.biz_footer.setStyleSheet(_INPUT); self.biz_footer.setPlaceholderText("Receipt footer message")

        for lbl_text, widget in [
            ("Business Name", self.biz_name),
            ("Address",       self.biz_address),
            ("Phone",         self.biz_phone),
            ("Receipt Footer",self.biz_footer),
        ]:
            lbl = QLabel(lbl_text); lbl.setStyleSheet(lbl_s)
            form.addRow(lbl, widget)

        layout.addLayout(form)
        layout.addStretch()

        self.biz_info_feedback = QLabel("")
        self.biz_info_feedback.setStyleSheet("color: #3dd68c; font-size: 11px; font-weight: 600;")
        self.biz_info_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.biz_info_feedback)

        save_btn = QPushButton("💾  Save Business Info")
        save_btn.setFixedHeight(38)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(_BTN_BLUE)
        save_btn.clicked.connect(self._biz_save_info)
        layout.addWidget(save_btn)

        self._biz_load_info()
        return panel

    def _biz_load_info(self):
        try:
            conn = get_business_conn()
            row = conn.execute(
                "SELECT business_name, address, phone, receipt_footer FROM business_info WHERE id=1"
            ).fetchone()
            conn.close()
        except Exception:
            row = None
        if row:
            self.biz_name.setText(row[0] or "")
            self.biz_address.setText(row[1] or "")
            self.biz_phone.setText(row[2] or "")
            self.biz_footer.setText(row[3] or "")

    def _biz_save_info(self):
        try:
            conn = get_business_conn()
            conn.execute("""
                UPDATE business_info
                SET business_name=?, address=?, phone=?, receipt_footer=?
                WHERE id=1
            """, (
                self.biz_name.text().strip(),
                self.biz_address.text().strip(),
                self.biz_phone.text().strip(),
                self.biz_footer.text().strip(),
            ))
            conn.commit()
            conn.close()
            self.biz_info_feedback.setStyleSheet("color: #3dd68c; font-size: 11px; font-weight: 600;")
            self.biz_info_feedback.setText("✓ Business info saved.")
        except Exception as e:
            self.biz_info_feedback.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 600;")
            self.biz_info_feedback.setText(str(e))

    # ── Settings panel (GCT, discount levels, product groups) ─────────

    def _build_biz_settings_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollBar:vertical { background: #161b22; width: 6px; } QScrollBar::handle:vertical { background: #30363d; border-radius: 3px; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(container)
        vbox.setSpacing(12)
        vbox.setContentsMargins(0, 0, 0, 0)

        vbox.addWidget(self._build_gct_panel())
        vbox.addWidget(self._build_case_profit_panel())
        vbox.addWidget(self._build_printer_settings_panel())
        vbox.addWidget(self._build_discount_panel())
        vbox.addWidget(self._build_groups_panel())
        vbox.addStretch()

        scroll.setWidget(container)
        return scroll

    # ── GCT panel ─────────────────────────────────────────────────────

    def _build_gct_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background: #0d1117; border-radius: 8px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("TAX (GCT) RATE")
        title.setStyleSheet(_SECTION_LBL)
        layout.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(_DIVIDER)
        layout.addWidget(sep)

        row = QHBoxLayout()
        lbl = QLabel("GCT %:")
        lbl.setStyleSheet("color: #c9d1d9; font-size: 13px;")

        self.gct_spin = QDoubleSpinBox()
        self.gct_spin.setFixedHeight(34)
        self.gct_spin.setRange(0.0, 100.0)
        self.gct_spin.setDecimals(2)
        self.gct_spin.setSuffix("  %")
        self.gct_spin.setStyleSheet(_INPUT)

        self.gct_feedback = QLabel("")
        self.gct_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")

        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(34)
        save_btn.setFixedWidth(70)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(_BTN_BLUE)
        save_btn.clicked.connect(self._gct_save)

        row.addWidget(lbl)
        row.addWidget(self.gct_spin, stretch=1)
        row.addWidget(save_btn)
        layout.addLayout(row)
        layout.addWidget(self.gct_feedback)

        self._gct_load()
        return panel

    def _gct_load(self):
        try:
            conn = get_business_conn()
            row = conn.execute("SELECT tax_percent FROM business_info WHERE id=1").fetchone()
            conn.close()
            if row:
                self.gct_spin.setValue(row[0])
        except Exception:
            pass

    def _gct_save(self):
        try:
            conn = get_business_conn()
            conn.execute("UPDATE business_info SET tax_percent=? WHERE id=1", (self.gct_spin.value(),))
            conn.commit()
            conn.close()
            self.gct_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")
            self.gct_feedback.setText("✓ GCT rate saved.")
        except Exception as e:
            self.gct_feedback.setStyleSheet("color: #f87171; font-size: 11px;")
            self.gct_feedback.setText(str(e))

            self.gct_feedback.setText(str(e))

    # ── Case profit panel ─────────────────────────────────────────────

    def _build_case_profit_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background: #0d1117; border-radius: 8px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("CASE PROFIT %")
        title.setStyleSheet(_SECTION_LBL)
        layout.addWidget(title)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(_DIVIDER); layout.addWidget(sep)

        desc = QLabel(
            "Profit markup applied to all case products.\n"
            "Case cost = single item cost × case quantity.\n"
            "Selling price = case cost × (1 + case profit %)."
        )
        desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        row = QHBoxLayout()
        lbl = QLabel("Case Profit %:")
        lbl.setStyleSheet("color: #c9d1d9; font-size: 13px;")

        self.case_profit_spin = QDoubleSpinBox()
        self.case_profit_spin.setFixedHeight(34)
        self.case_profit_spin.setRange(0.0, 500.0)
        self.case_profit_spin.setDecimals(2)
        self.case_profit_spin.setSuffix("  %")
        self.case_profit_spin.setStyleSheet(_INPUT)

        self.case_profit_feedback = QLabel("")
        self.case_profit_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")

        save_btn = QPushButton("Save")
        save_btn.setFixedHeight(34); save_btn.setFixedWidth(70)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(_BTN_BLUE)
        save_btn.clicked.connect(self._case_profit_save)

        row.addWidget(lbl)
        row.addWidget(self.case_profit_spin, stretch=1)
        row.addWidget(save_btn)
        layout.addLayout(row)
        layout.addWidget(self.case_profit_feedback)
        self._case_profit_load()
        return panel

    def _case_profit_load(self):
        try:
            conn = get_business_conn()
            row  = conn.execute(
                "SELECT case_profit_percent FROM business_info WHERE id=1"
            ).fetchone()
            conn.close()
            if row:
                self.case_profit_spin.setValue(row[0])
        except Exception:
            self.case_profit_spin.setValue(14.0)

    def _case_profit_save(self):
        try:
            new_pct = self.case_profit_spin.value()
            conn    = get_business_conn()
            conn.execute(
                "UPDATE business_info SET case_profit_percent=? WHERE id=1", (new_pct,)
            )
            conn.commit(); conn.close()
            self.case_profit_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")
            self.case_profit_feedback.setText("✓ Case profit saved.")
        except Exception as e:
            self.case_profit_feedback.setStyleSheet("color: #f87171; font-size: 11px;")
            self.case_profit_feedback.setText(str(e))

    # ── Printer settings panel ────────────────────────────────────────

    def _build_printer_settings_panel(self):
        from PyQt6.QtWidgets import QComboBox, QGroupBox
        panel = QFrame()
        panel.setStyleSheet("background: #0d1117; border-radius: 8px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("PRINTER SETTINGS")
        title.setStyleSheet(_SECTION_LBL)
        layout.addWidget(title)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(_DIVIDER); layout.addWidget(sep)

        def row_layout(label_text, widget):
            r = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(160)
            lbl.setStyleSheet("color: #c9d1d9; font-size: 13px;")
            r.addWidget(lbl)
            r.addWidget(widget, stretch=1)
            return r

        # Default printer type
        self.ps_type_combo = QComboBox()
        self.ps_type_combo.setFixedHeight(34)
        self.ps_type_combo.setStyleSheet(_INPUT)
        self.ps_type_combo.addItems(["Auto (thermal first)", "Thermal / Impact", "Normal Printer"])
        self.ps_type_combo.currentIndexChanged.connect(self._ps_on_type_changed)
        layout.addLayout(row_layout("Default Printer:", self.ps_type_combo))

        # Thermal connection type
        self.ps_conn_combo = QComboBox()
        self.ps_conn_combo.setFixedHeight(34)
        self.ps_conn_combo.setStyleSheet(_INPUT)
        self.ps_conn_combo.addItems(["USB", "Serial (COM)", "Parallel (LPT)", "Network (IP)"])
        self.ps_conn_combo.currentIndexChanged.connect(self._ps_on_conn_changed)
        layout.addLayout(row_layout("Thermal Connection:", self.ps_conn_combo))

        # Port / address field (shown for serial/parallel/network)
        self.ps_port_field = QLineEdit()
        self.ps_port_field.setFixedHeight(34)
        self.ps_port_field.setStyleSheet(_INPUT)
        self.ps_port_field.setPlaceholderText("e.g. COM3 / LPT1 / 192.168.1.100")
        self._ps_port_row = row_layout("Port / Address:", self.ps_port_field)
        layout.addLayout(self._ps_port_row)

        # Normal printer name
        self.ps_normal_combo = QComboBox()
        self.ps_normal_combo.setFixedHeight(34)
        self.ps_normal_combo.setStyleSheet(_INPUT)
        self._ps_populate_normal_printers()
        layout.addLayout(row_layout("Normal Printer:", self.ps_normal_combo))

        # Paper size
        self.ps_paper_combo = QComboBox()
        self.ps_paper_combo.setFixedHeight(34)
        self.ps_paper_combo.setStyleSheet(_INPUT)
        self.ps_paper_combo.addItems(["A4", "Letter", "Legal"])
        layout.addLayout(row_layout("Paper Size:", self.ps_paper_combo))

        # Receipt layout
        self.ps_layout_combo = QComboBox()
        self.ps_layout_combo.setFixedHeight(34)
        self.ps_layout_combo.setStyleSheet(_INPUT)
        self.ps_layout_combo.addItems(["3-Column (Product | GCT | Total)", "Simple (Product | Total)"])
        layout.addLayout(row_layout("Receipt Layout:", self.ps_layout_combo))

        # Feedback + Save
        self.ps_feedback = QLabel("")
        self.ps_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")

        save_btn = QPushButton("Save Printer Settings")
        save_btn.setFixedHeight(34)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(_BTN_BLUE)
        save_btn.clicked.connect(self._ps_save)

        layout.addWidget(self.ps_feedback)
        layout.addWidget(save_btn)

        self._ps_load()
        return panel

    def _ps_populate_normal_printers(self):
        """Populate the normal printer combo with system printers."""
        try:
            from printing.normal_printer import get_available_printers, get_default_printer
            printers = get_available_printers()
            self.ps_normal_combo.clear()
            self.ps_normal_combo.addItem("— System Default —", "")
            for name in printers:
                self.ps_normal_combo.addItem(name, name)
        except Exception:
            self.ps_normal_combo.addItem("— System Default —", "")

    def _ps_on_type_changed(self, idx):
        """Show/hide thermal fields based on printer type selection."""
        show_thermal = idx in (0, 1)  # Auto or Thermal
        self.ps_conn_combo.setEnabled(show_thermal)
        self.ps_port_field.setEnabled(show_thermal)

    def _ps_on_conn_changed(self, idx):
        """Show port field only when serial/parallel/network is selected."""
        # idx 0 = USB (no port needed), 1=Serial, 2=Parallel, 3=Network
        self.ps_port_field.setVisible(idx > 0)

    def _ps_load(self):
        """Load printer settings from business.db."""
        try:
            conn = get_business_conn()
            row  = conn.execute("""
                SELECT printer_type, thermal_connection, thermal_port,
                       paper_size, normal_printer_name, receipt_layout
                FROM business_info WHERE id=1
            """).fetchone()
            conn.close()
            if not row:
                return
            ptype, conn_type, port, paper, normal_name, layout = row

            type_map = {"auto": 0, "thermal": 1, "normal": 2}
            self.ps_type_combo.setCurrentIndex(type_map.get(ptype or "auto", 0))

            conn_map = {"usb": 0, "serial": 1, "parallel": 2, "network": 3}
            self.ps_conn_combo.setCurrentIndex(conn_map.get(conn_type or "usb", 0))

            self.ps_port_field.setText(port or "")

            paper_map = {"A4": 0, "Letter": 1, "Legal": 2}
            self.ps_paper_combo.setCurrentIndex(paper_map.get(paper or "A4", 0))

            layout_map = {"gct_column": 0, "simple": 1}
            self.ps_layout_combo.setCurrentIndex(layout_map.get(layout or "gct_column", 0))

            # Set normal printer
            for i in range(self.ps_normal_combo.count()):
                if self.ps_normal_combo.itemData(i) == (normal_name or ""):
                    self.ps_normal_combo.setCurrentIndex(i)
                    break

            self._ps_on_type_changed(self.ps_type_combo.currentIndex())
            self._ps_on_conn_changed(self.ps_conn_combo.currentIndex())
        except Exception as e:
            print(f"Printer settings load error: {e}")

    def _ps_save(self):
        """Save printer settings to business.db."""
        try:
            type_vals  = ["auto", "thermal", "normal"]
            conn_vals  = ["usb", "serial", "parallel", "network"]
            paper_vals = ["A4", "Letter", "Legal"]
            layout_vals = ["gct_column", "simple"]

            ptype     = type_vals[self.ps_type_combo.currentIndex()]
            conn_type = conn_vals[self.ps_conn_combo.currentIndex()]
            port      = self.ps_port_field.text().strip()
            paper     = paper_vals[self.ps_paper_combo.currentIndex()]
            normal    = self.ps_normal_combo.currentData() or ""
            layout    = layout_vals[self.ps_layout_combo.currentIndex()]

            conn = get_business_conn()
            conn.execute("""
                UPDATE business_info
                SET printer_type        = ?,
                    thermal_connection  = ?,
                    thermal_port        = ?,
                    paper_size          = ?,
                    normal_printer_name = ?,
                    receipt_layout      = ?
                WHERE id = 1
            """, (ptype, conn_type, port, paper, normal, layout))
            conn.commit()
            conn.close()

            self.ps_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")
            self.ps_feedback.setText("✓ Printer settings saved.")
        except Exception as e:
            self.ps_feedback.setStyleSheet("color: #f87171; font-size: 11px;")
            self.ps_feedback.setText(str(e))

    # ── Discount levels panel ─────────────────────────────────────────

    def _build_discount_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background: #0d1117; border-radius: 8px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("DISCOUNT LEVELS")
        title.setStyleSheet(_SECTION_LBL)
        add_btn = QPushButton("+ Add")
        add_btn.setFixedHeight(28)
        add_btn.setFixedWidth(60)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(_BTN_BLUE + "QPushButton { font-size: 11px; border-radius: 6px; }")
        add_btn.clicked.connect(self._disc_add_row)
        hdr.addWidget(title); hdr.addStretch(); hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(_DIVIDER)
        layout.addWidget(sep)

        self.disc_table = QTableWidget()
        self.disc_table.setColumnCount(4)
        self.disc_table.setHorizontalHeaderLabels(["Level Name", "Min Qty", "Discount %", ""])
        self.disc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.disc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.disc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.disc_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.disc_table.verticalHeader().setVisible(False)
        self.disc_table.setShowGrid(False)
        self.disc_table.setStyleSheet(_TABLE + "QTableWidget { min-height: 120px; }")
        layout.addWidget(self.disc_table)

        self.disc_feedback = QLabel("")
        self.disc_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")
        layout.addWidget(self.disc_feedback)

        save_btn = QPushButton("💾  Save Discount Levels")
        save_btn.setFixedHeight(34)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(_BTN_BLUE)
        save_btn.clicked.connect(self._disc_save)
        layout.addWidget(save_btn)

        self._disc_load()
        return panel

    def _disc_load(self):
        try:
            conn = get_products_conn()
            rows = conn.execute(
                "SELECT id, level_name, min_quantity, discount_percent FROM discount_levels ORDER BY min_quantity"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        self.disc_table.setRowCount(0)
        for r in rows:
            self._disc_insert_row(r[0], r[1], r[2], r[3])

    def _disc_add_row(self):
        self._disc_insert_row(None, "", 1, 0.0)

    def _disc_insert_row(self, row_id, name, min_qty, pct):
        row = self.disc_table.rowCount()
        self.disc_table.insertRow(row)

        name_edit = QLineEdit(name)
        name_edit.setFixedHeight(28)
        name_edit.setStyleSheet(_INPUT + "QLineEdit { border-radius: 5px; font-size: 11px; }")
        name_edit.setProperty("row_id", row_id)

        qty_spin = QSpinBox()
        qty_spin.setRange(1, 9999)
        qty_spin.setValue(min_qty)
        qty_spin.setFixedHeight(28)
        qty_spin.setStyleSheet(_INPUT + "QSpinBox { border-radius: 5px; font-size: 11px; }")

        pct_spin = QDoubleSpinBox()
        pct_spin.setRange(0.0, 100.0)
        pct_spin.setDecimals(2)
        pct_spin.setValue(pct)
        pct_spin.setSuffix("  %")
        pct_spin.setFixedHeight(28)
        pct_spin.setStyleSheet(_INPUT + "QDoubleSpinBox { border-radius: 5px; font-size: 11px; }")

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(_BTN_RED + "QPushButton { border-radius: 5px; font-size: 12px; padding: 0; }")
        del_btn.clicked.connect(lambda _, r=row: self._disc_delete_row(r, row_id))

        self.disc_table.setCellWidget(row, 0, name_edit)
        self.disc_table.setCellWidget(row, 1, qty_spin)
        self.disc_table.setCellWidget(row, 2, pct_spin)
        self.disc_table.setCellWidget(row, 3, del_btn)
        self.disc_table.setRowHeight(row, 36)

    def _disc_delete_row(self, row, row_id):
        if row_id is not None:
            try:
                conn = get_products_conn()
                conn.execute("DELETE FROM discount_levels WHERE id=?", (row_id,))
                conn.commit()
                conn.close()
            except Exception:
                pass
        self._disc_load()

    def _disc_save(self):
        try:
            conn = get_products_conn()
            for row in range(self.disc_table.rowCount()):
                name_w = self.disc_table.cellWidget(row, 0)
                qty_w  = self.disc_table.cellWidget(row, 1)
                pct_w  = self.disc_table.cellWidget(row, 2)
                if not name_w or not name_w.text().strip():
                    continue
                row_id = name_w.property("row_id")
                name   = name_w.text().strip()
                qty    = qty_w.value()
                pct    = pct_w.value()
                if row_id is None:
                    conn.execute(
                        "INSERT INTO discount_levels (level_name, min_quantity, discount_percent) VALUES (?,?,?)",
                        (name, qty, pct)
                    )
                else:
                    conn.execute(
                        "UPDATE discount_levels SET level_name=?, min_quantity=?, discount_percent=? WHERE id=?",
                        (name, qty, pct, row_id)
                    )
            conn.commit()
            conn.close()
            self.disc_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")
            self.disc_feedback.setText("✓ Discount levels saved.")
            self._disc_load()
        except Exception as e:
            self.disc_feedback.setStyleSheet("color: #f87171; font-size: 11px;")
            self.disc_feedback.setText(str(e))

    # ── Product groups panel ──────────────────────────────────────────

    def _build_groups_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background: #0d1117; border-radius: 8px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("PRODUCT GROUPS")
        title.setStyleSheet(_SECTION_LBL)
        add_btn = QPushButton("+ Add")
        add_btn.setFixedHeight(28)
        add_btn.setFixedWidth(60)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(_BTN_BLUE + "QPushButton { font-size: 11px; border-radius: 6px; }")
        add_btn.clicked.connect(self._grp_add_row)
        hdr.addWidget(title); hdr.addStretch(); hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(_DIVIDER)
        layout.addWidget(sep)

        self.grp_table = QTableWidget()
        self.grp_table.setColumnCount(3)
        self.grp_table.setHorizontalHeaderLabels(["Group Name", "Profit %", ""])
        self.grp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.grp_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.grp_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.grp_table.verticalHeader().setVisible(False)
        self.grp_table.setShowGrid(False)
        self.grp_table.setStyleSheet(_TABLE + "QTableWidget { min-height: 150px; }")
        layout.addWidget(self.grp_table)

        self.grp_feedback = QLabel("")
        self.grp_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")
        layout.addWidget(self.grp_feedback)

        save_btn = QPushButton("💾  Save Groups")
        save_btn.setFixedHeight(34)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(_BTN_BLUE)
        save_btn.clicked.connect(self._grp_save)
        layout.addWidget(save_btn)

        self._grp_load()
        return panel

    def _grp_load(self):
        try:
            conn = get_products_conn()
            rows = conn.execute(
                "SELECT id, group_name, profit_percent FROM product_groups ORDER BY group_name"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        self.grp_table.setRowCount(0)
        for r in rows:
            self._grp_insert_row(r[0], r[1], r[2])

    def _grp_add_row(self):
        self._grp_insert_row(None, "", 25.0)

    def _grp_insert_row(self, row_id, name, profit):
        row = self.grp_table.rowCount()
        self.grp_table.insertRow(row)

        name_edit = QLineEdit(name)
        name_edit.setFixedHeight(28)
        name_edit.setStyleSheet(_INPUT + "QLineEdit { border-radius: 5px; font-size: 11px; }")
        name_edit.setProperty("row_id", row_id)

        profit_spin = QDoubleSpinBox()
        profit_spin.setRange(0.0, 500.0)
        profit_spin.setDecimals(1)
        profit_spin.setValue(profit)
        profit_spin.setSuffix("  %")
        profit_spin.setFixedHeight(28)
        profit_spin.setStyleSheet(_INPUT + "QDoubleSpinBox { border-radius: 5px; font-size: 11px; }")

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(_BTN_RED + "QPushButton { border-radius: 5px; font-size: 12px; padding: 0; }")
        del_btn.clicked.connect(lambda _, rid=row_id: self._grp_delete_row(rid))

        self.grp_table.setCellWidget(row, 0, name_edit)
        self.grp_table.setCellWidget(row, 1, profit_spin)
        self.grp_table.setCellWidget(row, 2, del_btn)
        self.grp_table.setRowHeight(row, 36)

    def _grp_delete_row(self, row_id):
        if row_id is not None:
            try:
                conn = get_products_conn()
                conn.execute("DELETE FROM product_groups WHERE id=?", (row_id,))
                conn.commit()
                conn.close()
            except Exception:
                pass
        self._grp_load()

    def _grp_save(self):
        try:
            conn = get_products_conn()
            for row in range(self.grp_table.rowCount()):
                name_w   = self.grp_table.cellWidget(row, 0)
                profit_w = self.grp_table.cellWidget(row, 1)
                if not name_w or not name_w.text().strip():
                    continue
                row_id = name_w.property("row_id")
                name   = name_w.text().strip()
                profit = profit_w.value()
                if row_id is None:
                    conn.execute(
                        "INSERT INTO product_groups (group_name, profit_percent) VALUES (?,?)",
                        (name, profit)
                    )
                else:
                    conn.execute(
                        "UPDATE product_groups SET group_name=?, profit_percent=? WHERE id=?",
                        (name, profit, row_id)
                    )
            conn.commit()
            conn.close()
            self.grp_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")
            self.grp_feedback.setText("✓ Groups saved.")
            self._grp_load()
        except Exception as e:
            self.grp_feedback.setStyleSheet("color: #f87171; font-size: 11px;")
            self.grp_feedback.setText(str(e))

    # ================================================================
    # QUICK KEYS TAB
    # ================================================================

    def _build_quickkeys_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        desc = QLabel(
            "Assign a product to each F-key (F1–F8).  "
            "Start typing a product name to search — select from the results."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        ref_btn = QPushButton("↻  Refresh")
        ref_btn.setFixedHeight(32)
        ref_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ref_btn.setStyleSheet(_BTN_BLUE + "QPushButton { border-radius: 6px; }")
        ref_btn.clicked.connect(self._qk_load_products)
        hdr.addWidget(desc, stretch=1)
        hdr.addWidget(ref_btn)
        outer.addLayout(hdr)

        # Grid of 8 rows  — each row: F-label + _ProductSearchWidget
        grid = QFrame()
        grid.setStyleSheet("background: #0d1117; border-radius: 8px;")
        gl = QVBoxLayout(grid)
        gl.setContentsMargins(20, 16, 20, 16)
        gl.setSpacing(10)

        self._qk_widgets = []   # list of _ProductSearchWidget, index = key_number-1
        for i in range(1, 9):
            row_w = QHBoxLayout()

            key_lbl = QLabel(f"F{i}")
            key_lbl.setFixedWidth(38)
            key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            key_lbl.setStyleSheet(
                "color: #ffffff; font-size: 14px; font-weight: 700;"
                "background: #21262d; border: 1px solid #30363d;"
                "border-radius: 5px; padding: 4px 0;"
            )

            sw = _ProductSearchWidget()
            sw.setProperty("key_number", i)
            self._qk_widgets.append(sw)

            row_w.addWidget(key_lbl)
            row_w.addWidget(sw, stretch=1)
            gl.addLayout(row_w)

        outer.addWidget(grid)

        self.qk_feedback = QLabel("")
        self.qk_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")

        save_btn = QPushButton("💾  Save Quick Keys")
        save_btn.setFixedHeight(36)
        save_btn.setFixedWidth(200)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(_BTN_BLUE)
        save_btn.clicked.connect(self._qk_save)

        outer.addWidget(self.qk_feedback)
        outer.addWidget(save_btn)
        outer.addStretch()

        self._qk_load_products()
        return w

    def _qk_load_products(self):
        """Load the product list into all 8 search widgets and restore saved assignments."""
        try:
            conn = get_products_conn()
            products = conn.execute(
                "SELECT id, name, selling_price FROM products ORDER BY name"
            ).fetchall()
            assigned = {
                r[0]: r[1]
                for r in conn.execute(
                    "SELECT key_number, product_id FROM quick_keys"
                ).fetchall()
            }
            # Build a name lookup for display
            name_map = {pid: (name, price) for pid, name, price in products}
            conn.close()
        except Exception:
            products = []
            assigned = {}
            name_map = {}

        product_tuples = [(pid, name, price) for pid, name, price in products]

        for sw in self._qk_widgets:
            kn = sw.property("key_number")
            sw.set_products(product_tuples)
            pid = assigned.get(kn)
            if pid and pid in name_map:
                name, price = name_map[pid]
                sw.set_selection(pid, f"{name}  (${price:.2f})")
            else:
                sw.clear_selection()

    def _qk_save(self):
        try:
            conn = get_products_conn()
            conn.execute("DELETE FROM quick_keys")
            for sw in self._qk_widgets:
                pid = sw.currentData()
                if pid is not None:
                    conn.execute(
                        "INSERT OR REPLACE INTO quick_keys (key_number, product_id) VALUES (?,?)",
                        (sw.property("key_number"), pid)
                    )
            conn.commit()
            conn.close()
            self.qk_feedback.setStyleSheet("color: #3dd68c; font-size: 11px;")
            self.qk_feedback.setText("✓ Quick keys saved. Cashiers will see changes on next login.")
        except Exception as e:
            self.qk_feedback.setStyleSheet("color: #f87171; font-size: 11px;")
            self.qk_feedback.setText(str(e))

    # ================================================================
    # POSTGRESQL SYNC TAB
    # ================================================================

    def _build_sync_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # ── Connection settings ──────────────────────────────────────
        cfg_frame = QFrame()
        cfg_frame.setStyleSheet("background: #0d1117; border-radius: 8px;")
        cfg_l = QVBoxLayout(cfg_frame)
        cfg_l.setContentsMargins(20, 16, 20, 16)
        cfg_l.setSpacing(10)

        cfg_title = QLabel("POSTGRESQL CONNECTION")
        cfg_title.setStyleSheet(_SECTION_LBL)
        cfg_l.addWidget(cfg_title)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(_DIVIDER)
        cfg_l.addWidget(sep)

        self.sync_enabled = QCheckBox("Enable PostgreSQL sync")
        self.sync_enabled.setStyleSheet("color: #c9d1d9; font-size: 13px;")
        cfg_l.addWidget(self.sync_enabled)

        def cfg_row(label, widget):
            r = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(100)
            lbl.setStyleSheet("color: #c9d1d9; font-size: 13px;")
            r.addWidget(lbl); r.addWidget(widget, stretch=1)
            return r

        self.sync_host = QLineEdit(); self.sync_host.setFixedHeight(32); self.sync_host.setStyleSheet(_INPUT)
        self.sync_port = QLineEdit(); self.sync_port.setFixedHeight(32); self.sync_port.setStyleSheet(_INPUT)
        self.sync_db   = QLineEdit(); self.sync_db.setFixedHeight(32);   self.sync_db.setStyleSheet(_INPUT)
        self.sync_user = QLineEdit(); self.sync_user.setFixedHeight(32); self.sync_user.setStyleSheet(_INPUT)
        self.sync_pw   = QLineEdit(); self.sync_pw.setFixedHeight(32);   self.sync_pw.setStyleSheet(_INPUT)
        self.sync_pw.setEchoMode(QLineEdit.EchoMode.Password)

        cfg_l.addLayout(cfg_row("Host:",     self.sync_host))
        cfg_l.addLayout(cfg_row("Port:",     self.sync_port))
        cfg_l.addLayout(cfg_row("Database:", self.sync_db))
        cfg_l.addLayout(cfg_row("User:",     self.sync_user))
        cfg_l.addLayout(cfg_row("Password:", self.sync_pw))

        cfg_btn_row = QHBoxLayout()
        save_cfg_btn = QPushButton("💾  Save Config")
        save_cfg_btn.setFixedHeight(32); save_cfg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_cfg_btn.setStyleSheet(_BTN_BLUE + "QPushButton { border-radius: 6px; }")
        save_cfg_btn.clicked.connect(self._sync_save_config)
        test_btn = QPushButton("🔌  Test Connection")
        test_btn.setFixedHeight(32); test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.setStyleSheet(_BTN_BLUE + "QPushButton { border-radius: 6px; }")
        test_btn.clicked.connect(self._sync_test)
        cfg_btn_row.addWidget(save_cfg_btn); cfg_btn_row.addWidget(test_btn); cfg_btn_row.addStretch()
        cfg_l.addLayout(cfg_btn_row)

        self.sync_cfg_status = QLabel("")
        self.sync_cfg_status.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.sync_cfg_status.setWordWrap(True)
        cfg_l.addWidget(self.sync_cfg_status)

        # ── Sync actions ─────────────────────────────────────────────
        act_frame = QFrame()
        act_frame.setStyleSheet("background: #0d1117; border-radius: 8px;")
        act_l = QVBoxLayout(act_frame)
        act_l.setContentsMargins(20, 16, 20, 16)
        act_l.setSpacing(10)

        act_title = QLabel("SYNC ACTIONS")
        act_title.setStyleSheet(_SECTION_LBL)
        act_l.addWidget(act_title)
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine); sep2.setStyleSheet(_DIVIDER)
        act_l.addWidget(sep2)

        desc = QLabel(
            "Push sends all local data to PostgreSQL.\n"
            "Pull brings remote products/users/settings to this terminal.\n"
            "Transaction history is never overwritten on pull."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        act_l.addWidget(desc)

        act_btn_row = QHBoxLayout()
        schema_btn = QPushButton("🔧  Mirror Schema")
        push_btn   = QPushButton("⬆  Push to Remote")
        pull_btn   = QPushButton("⬇  Pull from Remote")
        sync_btn   = QPushButton("🔄  Full Sync")

        for b, slot, bg in [
            (schema_btn, self._sync_schema,  "#21262d"),
            (push_btn,   self._sync_push,    "#1a56db"),
            (pull_btn,   self._sync_pull,    "#14532d"),
            (sync_btn,   self._sync_full,    "#7c3aed"),
        ]:
            b.setFixedHeight(34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"QPushButton {{ background: {bg}; color: #fff; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; padding: 0 12px; }} QPushButton:hover {{ opacity: 0.85; }}")
            b.clicked.connect(slot)
            act_btn_row.addWidget(b)

        act_l.addLayout(act_btn_row)

        self.sync_result = QLabel("")
        self.sync_result.setWordWrap(True)
        self.sync_result.setStyleSheet("color: #c9d1d9; font-size: 11px; font-family: monospace;")
        act_l.addWidget(self.sync_result)

        # ── Sync log ──────────────────────────────────────────────────
        log_frame = QFrame()
        log_frame.setStyleSheet("background: #0d1117; border-radius: 8px;")
        log_l = QVBoxLayout(log_frame)
        log_l.setContentsMargins(12, 12, 12, 12)
        log_l.setSpacing(6)

        log_hdr = QHBoxLayout()
        log_title = QLabel("SYNC LOG")
        log_title.setStyleSheet(_SECTION_LBL)
        ref_log = QPushButton("↻"); ref_log.setFixedSize(28, 24)
        ref_log.setStyleSheet(_BTN_BLUE + "QPushButton { border-radius: 4px; font-size: 12px; padding: 0; }")
        ref_log.clicked.connect(self._sync_load_log)
        log_hdr.addWidget(log_title); log_hdr.addStretch(); log_hdr.addWidget(ref_log)
        log_l.addLayout(log_hdr)

        self.sync_log_table = QTableWidget()
        self.sync_log_table.setColumnCount(5)
        self.sync_log_table.setHorizontalHeaderLabels(["Time", "Event", "Table", "Rows", "Message"])
        self.sync_log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.sync_log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.sync_log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.sync_log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.sync_log_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.sync_log_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sync_log_table.verticalHeader().setVisible(False)
        self.sync_log_table.setShowGrid(False)
        self.sync_log_table.setFixedHeight(160)
        self.sync_log_table.setStyleSheet(_TABLE)
        log_l.addWidget(self.sync_log_table)

        outer.addWidget(cfg_frame)
        outer.addWidget(act_frame)
        outer.addWidget(log_frame)
        outer.addStretch()

        self._sync_load_config()
        self._sync_load_log()
        return w

    # ── Sync helpers ───────────────────────────────────────────────────

    def _sync_load_config(self):
        """Populate fields from config.py values."""
        try:
            import importlib, config as _cfg
            self.sync_enabled.setChecked(bool(_cfg.USE_POSTGRES))
            c = _cfg.POSTGRES_CONFIG
            self.sync_host.setText(str(c.get("host", "localhost")))
            self.sync_port.setText(str(c.get("port", 5432)))
            self.sync_db.setText(str(c.get("database", "pos_db")))
            self.sync_user.setText(str(c.get("user", "pos_user")))
            self.sync_pw.setText(str(c.get("password", "")))
        except Exception:
            pass

    def _sync_save_config(self):
        """Write updated connection settings back to config.py."""
        try:
            import config as _cfg
            from pathlib import Path
            cfg_path = Path(_cfg.__file__)
            text = cfg_path.read_text()

            def _replace(text, key, value):
                import re
                if isinstance(value, str):
                    return re.sub(rf'("{key}":\s*)("[^"]*")', rf'\g<1>"{value}"', text)
                else:
                    return re.sub(rf'("{key}":\s*)(\d+)', rf'\g<1>{value}', text)

            use = "True" if self.sync_enabled.isChecked() else "False"
            text = re.sub(r'USE_POSTGRES\s*=\s*(True|False)', f'USE_POSTGRES = {use}', text)
            text = _replace(text, "host",     self.sync_host.text().strip())
            text = _replace(text, "database", self.sync_db.text().strip())
            text = _replace(text, "user",     self.sync_user.text().strip())
            text = _replace(text, "password", self.sync_pw.text())
            try:
                port = int(self.sync_port.text().strip())
                text = _replace(text, "port", port)
            except ValueError:
                pass
            cfg_path.write_text(text)
            self.sync_cfg_status.setStyleSheet("color: #3dd68c; font-size: 11px;")
            self.sync_cfg_status.setText("✓ Config saved. Restart required for USE_POSTGRES to take effect.")
        except Exception as e:
            self.sync_cfg_status.setStyleSheet("color: #f87171; font-size: 11px;")
            self.sync_cfg_status.setText(f"Save failed: {e}")

    def _sync_run(self, action, label):
        """Generic runner: applies temp config override, runs action, shows result."""
        import re
        # Temporarily patch the in-memory config with form values
        try:
            import config as _cfg
            _cfg.USE_POSTGRES = self.sync_enabled.isChecked()
            _cfg.POSTGRES_CONFIG["host"]     = self.sync_host.text().strip()
            _cfg.POSTGRES_CONFIG["port"]     = int(self.sync_port.text().strip() or "5432")
            _cfg.POSTGRES_CONFIG["database"] = self.sync_db.text().strip()
            _cfg.POSTGRES_CONFIG["user"]     = self.sync_user.text().strip()
            _cfg.POSTGRES_CONFIG["password"] = self.sync_pw.text()
        except Exception:
            pass

        from db.sync import SyncManager
        sm  = SyncManager()
        ok, msg = action(sm)
        color = "#3dd68c" if ok else "#f87171"
        self.sync_result.setStyleSheet(f"color: {color}; font-size: 11px; font-family: monospace;")
        self.sync_result.setText(msg)
        self._sync_load_log()

    def _sync_test(self):
        self._sync_run(lambda sm: sm.test_connection(), "Test")

    def _sync_schema(self):
        self._sync_run(lambda sm: sm.ensure_schema(), "Mirror Schema")

    def _sync_push(self):
        self._sync_run(lambda sm: sm.push_all(), "Push")

    def _sync_pull(self):
        self._sync_run(lambda sm: sm.pull_all(), "Pull")

    def _sync_full(self):
        self._sync_run(lambda sm: sm.sync(), "Full Sync")

    def _sync_load_log(self):
        try:
            from db.sync import SyncManager
            entries = SyncManager().get_log(50)
        except Exception:
            entries = []
        tbl = self.sync_log_table
        tbl.setRowCount(len(entries))
        ec = {"push": "#4493f8", "pull": "#3dd68c", "error": "#f87171",
              "test": "#a78bfa", "sync": "#f59e0b"}
        for i, e in enumerate(entries):
            ti = QTableWidgetItem(e["time"] or "")
            ti.setForeground(QColor("#8b949e"))
            ev = QTableWidgetItem(e["event"] or "")
            ev.setForeground(QColor(ec.get(e["event"], "#c9d1d9")))
            tb = QTableWidgetItem(e["table"] or "")
            ri = QTableWidgetItem(str(e["rows"] or ""))
            ri.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            mi = QTableWidgetItem(e["message"] or "")
            mi.setForeground(QColor("#8b949e"))
            for col, item in enumerate([ti, ev, tb, ri, mi]):
                tbl.setItem(i, col, item)
            tbl.setRowHeight(i, 28)
