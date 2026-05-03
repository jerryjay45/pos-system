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
    QListWidget, QListWidgetItem, QFileDialog, QProgressBar,
    QTextEdit, QDialog
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QDoubleValidator

from ui.supervisor_dashboard import SupervisorDashboard
from db import get_users_conn, get_business_conn, get_products_conn


# ──────────────────────────────────────────────────────────────────────────────
# SHARED STYLE CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

_BTN_BLUE = """
    QPushButton {
        background-color: #f59e0b; color: #ffffff;
        border: none; border-radius: 8px;
        font-size: 13px; font-weight: 600; padding: 0 18px;
    }
    QPushButton:hover  { background-color: #d97706; }
    QPushButton:pressed{ background-color: #b45309; }
    QPushButton:disabled{ background-color: #1a2540; color: #4a5a7a; }
"""
_BTN_RED = """
    QPushButton {
        background: #ef444422; color: #fca5a5;
        border: none; border-radius: 8px;
        font-size: 12px; font-weight: 600; padding: 0 14px;
    }
    QPushButton:hover  { background: #dc2626; }
    QPushButton:pressed{ background: #b91c1c; }
    QPushButton:disabled{ background: #2d1515; color: #6b3030; }
"""
_BTN_GREEN = """
    QPushButton {
        background: #10b98122; color: #6ee7b7;
        border: none; border-radius: 8px;
        font-size: 12px; font-weight: 600; padding: 0 14px;
    }
    QPushButton:hover  { background: #059669; }
    QPushButton:pressed{ background: #15803d; }
    QPushButton:disabled{ background: #0d2b18; color: #3a6b4a; }
"""
_BTN_OUTLINE = """
    QPushButton {
        background: #0d1e2e; color: #94aac4;
        border: 1.5px solid #2d5282; border-radius: 8px;
        font-size: 12px; font-weight: 600; padding: 0 14px;
    }
    QPushButton:hover  { background: #1e3a5f; color: #f59e0b; border-color: #f59e0b; }
    QPushButton:pressed{ background: #f59e0b22; }
    QPushButton:disabled{ color: #334155; border-color: #1e293b; }
"""
_INPUT = """
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
        background-color: #0b1120; color: #ffffff;
        border: 1.5px solid #1e3a5f; border-radius: 8px;
        padding: 0 12px; font-size: 13px;
    }
    QLineEdit:focus, QComboBox:focus,
    QDoubleSpinBox:focus, QSpinBox:focus { border-color: #f59e0b; }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox QAbstractItemView {
        background: #0b1120; color: #94a3b8;
        border: 1px solid #1e3a5f; selection-background-color: #f59e0b; selection-color: #0a0400;
    }
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
    QSpinBox::up-button, QSpinBox::down-button {
        background: #1e293b; border: none; width: 18px;
    }
"""
_TABLE = """
    QTableWidget { background: transparent; color: #f0f6ff; border: none; font-size: 13px; }
    QTableWidget::item { padding: 8px; border-bottom: 1px solid #1e3a5f; color: #f0f6ff; }
    QTableWidget::item:selected { background-color: #f59e0b55; color: #fbbf24; }
    QTableWidget::item:hover { background-color: #172840; }
    QHeaderView::section { background: #0a1929; color: #f59e0b; border: none; padding: 8px;
                           font-size: 11px; font-weight: 700;
                           border-bottom: 2px solid #f59e0b; }
"""
_SECTION_LBL = "color: #f59e0b; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
_DIVIDER     = "background: #1e3a5f;"


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
            background-color: #0b1120; color: #ffffff;
            border: 1.5px solid #1e3a5f; border-radius: 8px;
            padding: 0 12px; font-size: 13px;
        }
        QLineEdit:focus { border-color: #f59e0b; }
    """
    _LIST_STYLE = """
        QListWidget {
            background-color: #0d1f2d; color: #94a3b8;
            border: 1.5px solid #f59e0b; border-radius: 0 0 8px 8px;
            border-top: none; font-size: 12px;
        }
        QListWidget::item { padding: 7px 12px; border-bottom: 1px solid #1e293b; }
        QListWidget::item:selected { background-color: #f59e0b; color: #0a0400; }
        QListWidget::item:hover    { background-color: #1e293b; }
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

    def __init__(self, user_id, full_name, app=None):
        # Call SupervisorDashboard __init__ passing app through
        super().__init__(user_id, full_name, role="manager", app=app)

    # ── Override window title & tab order ────────────────────────────

    def _build_ui(self):
        """Override to inject manager tabs first."""
        from PyQt6.QtWidgets import QVBoxLayout, QWidget
        root = QWidget()
        root.setStyleSheet("background-color: #0b1120;")
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
        bar.setMinimumHeight(44)
        bar.setMaximumHeight(56)
        # Manager: deep purple topbar — visually distinct from supervisor (green) and cashier (blue)
        bar.setStyleSheet("background-color: #1a0a2e; border-radius: 10px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        left = QLabel(f"POS System  |  Manager:  {self.full_name}")
        left.setStyleSheet("color: #e9d5ff; font-size: 15px; font-weight: 600;")

        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_label.setStyleSheet("color: #c4b5fd; font-size: 14px;")

        from ui.theme_toggle import ZoomWidget
        zoom_w = ZoomWidget(self._app if hasattr(self, "_app") else None)

        logout_btn = QPushButton("Logout  ↗")
        logout_btn.setMinimumWidth(100)
        logout_btn.setMinimumHeight(32)
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d1b4e; color: #e9d5ff;
                border: 1.5px solid #4c1d95; border-radius: 18px;
                font-size: 13px; font-weight: 700;
            }
            QPushButton:hover   { background-color: #3b0764; border-color: #7c3aed; }
            QPushButton:pressed { background-color: #4c1d95; }
        """)
        logout_btn.clicked.connect(self._handle_logout)

        layout.addWidget(left)
        layout.addStretch()
        layout.addWidget(self.clock_label)
        layout.addStretch()
        layout.addWidget(zoom_w)
        layout.addSpacing(8)
        layout.addWidget(logout_btn)
        return bar

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #0d1f2d;
                border: none;
                border-radius: 0 8px 8px 8px;
            }
            QTabBar::tab {
                background-color: #1e293b;
                color: #64748b;
                border: 1px solid #1e3a5f;
                border-bottom: none;
                border-radius: 6px 6px 0 0;
                padding: 8px 20px;
                font-size: 13px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0d1f2d;
                color: #ffffff;
                font-weight: 700;
            }
            QTabBar::tab:hover { background-color: #1e3a5f; color: #ffffff; }
        """)

        # Manager-only tabs first
        self.tabs.addTab(self._build_users_tab(),      "👥  Users")
        self.tabs.addTab(self._build_business_tab(),   "🏢  Business")
        self.tabs.addTab(self._build_quickkeys_tab(),  "⌨  Quick Keys")
        self.tabs.addTab(self._build_dbf_tab(),        "📥  Import DBF")
        self.tabs.addTab(self._build_sync_tab(),       "🔄  PostgreSQL")

        # Inherited supervisor tabs
        self.tabs.addTab(self._build_products_tab(),     "🏷  Products")
        self.tabs.addTab(self._build_reports_tab(),      "📊  Reports")
        self.tabs.addTab(self._build_transactions_tab(), "🧾  Transactions")
        self.tabs.addTab(self._build_void_tab(),         "↩  Void / Refund")
        self.tabs.addTab(self._build_labels_tab(),       "🏷  Labels")

        self.tabs.setCurrentIndex(0)
        return self.tabs

    # ================================================================
    # USERS TAB
    # ================================================================

    def _build_users_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #0d1f2d;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Left: user list ──────────────────────────────────────────
        left = QFrame()
        left.setStyleSheet("background: #0b1120; border-radius: 8px;")
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
        self.usr_role_filter.setMinimumHeight(32)
        self.usr_role_filter.setMinimumWidth(110)
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
        right.setMinimumWidth(260)
        right.setMaximumWidth(380)
        right.setStyleSheet("background: #0b1120; border-radius: 8px;")
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

        lbl_style = "color: #64748b; font-size: 12px;"

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
        self.usr_f_active.setStyleSheet("color: #94a3b8; font-size: 13px;")

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
        self.usr_feedback.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 600;")
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
        role_colors = {"cashier": "#60a5fa", "supervisor": "#fcd34d", "manager": "#ef4444"}
        for u in users:
            row = tbl.rowCount()
            tbl.insertRow(row)

            name_item = QTableWidgetItem(u["full_name"])
            name_item.setData(Qt.ItemDataRole.UserRole, u["id"])
            name_item.setForeground(QColor("#ffffff"))

            user_item   = QTableWidgetItem(u["username"])
            role_item   = QTableWidgetItem(u["role"].capitalize())
            role_item.setForeground(QColor(role_colors.get(u["role"], "#94a3b8")))
            role_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            status_text = "Active" if u["is_active"] else "Inactive"
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor("#10b981" if u["is_active"] else "#ef4444"))
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
            self.usr_feedback.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 600;")
            self.usr_feedback.setText("Full name and username are required.")
            return
        if self._usr_editing_id is None and not password:
            self.usr_feedback.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 600;")
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
            self.usr_feedback.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 600;")
            self.usr_feedback.setText(msg)
            self._usr_load()
            self._usr_new_form()
        except Exception as e:
            self.usr_feedback.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 600;")
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
        w.setStyleSheet("background-color: #0d1f2d;")
        main = QHBoxLayout(w)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)

        main.addWidget(self._build_biz_info_panel(), stretch=1)
        main.addWidget(self._build_biz_settings_panel(), stretch=1)
        return w

    # ── Business info panel ───────────────────────────────────────────

    def _build_biz_info_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background: #0b1120; border-radius: 8px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("BUSINESS INFORMATION")
        title.setStyleSheet(_SECTION_LBL)
        layout.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(_DIVIDER)
        layout.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_s = "color: #64748b; font-size: 12px;"

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
        self.biz_info_feedback.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 600;")
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
            self.biz_info_feedback.setStyleSheet("color: #10b981; font-size: 11px; font-weight: 600;")
            self.biz_info_feedback.setText("✓ Business info saved.")
        except Exception as e:
            self.biz_info_feedback.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: 600;")
            self.biz_info_feedback.setText(str(e))

    # ── Settings panel (GCT, discount levels, product groups) ─────────

    def _build_biz_settings_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; } QScrollBar:vertical { background: #0d1f2d; width: 6px; } QScrollBar::handle:vertical { background: #1e3a5f; border-radius: 3px; }")

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
        panel.setStyleSheet("background: #0b1120; border-radius: 8px;")
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
        lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")

        self.gct_spin = QDoubleSpinBox()
        self.gct_spin.setFixedHeight(34)
        self.gct_spin.setRange(0.0, 100.0)
        self.gct_spin.setDecimals(2)
        self.gct_spin.setSuffix("  %")
        self.gct_spin.setStyleSheet(_INPUT)

        self.gct_feedback = QLabel("")
        self.gct_feedback.setStyleSheet("color: #10b981; font-size: 11px;")

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
            self.gct_feedback.setStyleSheet("color: #10b981; font-size: 11px;")
            self.gct_feedback.setText("✓ GCT rate saved.")
        except Exception as e:
            self.gct_feedback.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.gct_feedback.setText(str(e))

            self.gct_feedback.setText(str(e))

    # ── Case profit panel ─────────────────────────────────────────────

    def _build_case_profit_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background: #0b1120; border-radius: 8px;")
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
        desc.setStyleSheet("color: #64748b; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        row = QHBoxLayout()
        lbl = QLabel("Case Profit %:")
        lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")

        self.case_profit_spin = QDoubleSpinBox()
        self.case_profit_spin.setFixedHeight(34)
        self.case_profit_spin.setRange(0.0, 500.0)
        self.case_profit_spin.setDecimals(2)
        self.case_profit_spin.setSuffix("  %")
        self.case_profit_spin.setStyleSheet(_INPUT)

        self.case_profit_feedback = QLabel("")
        self.case_profit_feedback.setStyleSheet("color: #10b981; font-size: 11px;")

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
            self.case_profit_feedback.setStyleSheet("color: #10b981; font-size: 11px;")
            self.case_profit_feedback.setText("✓ Case profit saved.")
        except Exception as e:
            self.case_profit_feedback.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.case_profit_feedback.setText(str(e))

    # ── Printer settings panel ────────────────────────────────────────

    def _build_printer_settings_panel(self):
        from PyQt6.QtWidgets import QComboBox, QGroupBox
        panel = QFrame()
        panel.setStyleSheet("background: #0b1120; border-radius: 8px;")
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
            lbl.setMinimumWidth(130)
            lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")
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
        self.ps_feedback.setStyleSheet("color: #10b981; font-size: 11px;")

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

            self.ps_feedback.setStyleSheet("color: #10b981; font-size: 11px;")
            self.ps_feedback.setText("✓ Printer settings saved.")
        except Exception as e:
            self.ps_feedback.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.ps_feedback.setText(str(e))

    # ── Discount levels panel ─────────────────────────────────────────

    def _build_discount_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background: #0b1120; border-radius: 8px;")
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
        self.disc_feedback.setStyleSheet("color: #10b981; font-size: 11px;")
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
            self.disc_feedback.setStyleSheet("color: #10b981; font-size: 11px;")
            self.disc_feedback.setText("✓ Discount levels saved.")
            self._disc_load()
        except Exception as e:
            self.disc_feedback.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.disc_feedback.setText(str(e))

    # ── Product groups panel ──────────────────────────────────────────

    def _build_groups_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background: #0b1120; border-radius: 8px;")
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
        self.grp_feedback.setStyleSheet("color: #10b981; font-size: 11px;")
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
            self.grp_feedback.setStyleSheet("color: #10b981; font-size: 11px;")
            self.grp_feedback.setText("✓ Groups saved.")
            self._grp_load()
        except Exception as e:
            self.grp_feedback.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.grp_feedback.setText(str(e))

    # ================================================================
    # QUICK KEYS TAB
    # ================================================================

    def _build_quickkeys_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #0d1f2d;")
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
        desc.setStyleSheet("color: #64748b; font-size: 13px;")
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
        grid.setStyleSheet("background: #0b1120; border-radius: 8px;")
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
                "background: #1e293b; border: 1px solid #1e3a5f;"
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
        self.qk_feedback.setStyleSheet("color: #10b981; font-size: 11px;")

        save_btn = QPushButton("💾  Save Quick Keys")
        save_btn.setMinimumHeight(34)
        save_btn.setMinimumWidth(160)
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
            self.qk_feedback.setStyleSheet("color: #10b981; font-size: 11px;")
            self.qk_feedback.setText("✓ Quick keys saved. Cashiers will see changes on next login.")
        except Exception as e:
            self.qk_feedback.setStyleSheet("color: #ef4444; font-size: 11px;")
            self.qk_feedback.setText(str(e))

    # ================================================================
    # DBF IMPORT TAB
    # ================================================================

    def _build_dbf_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #0f1f30;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("Import Stock from DBF File")
        title.setStyleSheet("color: #f0f6ff; font-size: 16px; font-weight: 700;")
        desc = QLabel(
            "Imports products from a dBase (.DBF) file — e.g. STOCK.DBF — "
            "into the products database. Groups, discount tiers, and stock "
            "quantities are created automatically. Duplicate barcodes are skipped."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94aac4; font-size: 12px;")
        hdr.addWidget(title)
        layout.addLayout(hdr)
        layout.addWidget(desc)

        # ── File picker row ───────────────────────────────────────────
        file_frame = QFrame()
        file_frame.setStyleSheet("background: #0a1929; border-radius: 8px;")
        fl = QVBoxLayout(file_frame)
        fl.setContentsMargins(16, 14, 16, 14)
        fl.setSpacing(8)

        file_lbl = QLabel("DBF FILE")
        file_lbl.setStyleSheet(_SECTION_LBL)
        fl.addWidget(file_lbl)

        file_row = QHBoxLayout()
        self.dbf_path_edit = QLineEdit()
        self.dbf_path_edit.setPlaceholderText("Select a .DBF file…")
        self.dbf_path_edit.setReadOnly(True)
        self.dbf_path_edit.setFixedHeight(36)
        self.dbf_path_edit.setStyleSheet(_INPUT + "QLineEdit { color: #94aac4; }")

        browse_btn = QPushButton("📂  Browse…")
        browse_btn.setFixedHeight(36)
        browse_btn.setFixedWidth(130)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet(_BTN_BLUE)
        browse_btn.clicked.connect(self._dbf_browse)

        file_row.addWidget(self.dbf_path_edit, stretch=1)
        file_row.addWidget(browse_btn)
        fl.addLayout(file_row)

        # Preview row — shown after file selected
        self.dbf_preview_lbl = QLabel("")
        self.dbf_preview_lbl.setStyleSheet("color: #5a7a9a; font-size: 11px;")
        fl.addWidget(self.dbf_preview_lbl)

        layout.addWidget(file_frame)

        # ── Options ───────────────────────────────────────────────────
        opt_frame = QFrame()
        opt_frame.setStyleSheet("background: #0a1929; border-radius: 8px;")
        ol = QVBoxLayout(opt_frame)
        ol.setContentsMargins(16, 14, 16, 14)
        ol.setSpacing(8)

        opt_lbl = QLabel("OPTIONS")
        opt_lbl.setStyleSheet(_SECTION_LBL)
        ol.addWidget(opt_lbl)

        self.dbf_skip_dup = QCheckBox("Skip duplicate barcodes (recommended)")
        self.dbf_skip_dup.setChecked(True)
        self.dbf_skip_dup.setStyleSheet("color: #c9d1d9; font-size: 13px;")

        self.dbf_create_groups = QCheckBox("Create product groups from DBF GROUP field")
        self.dbf_create_groups.setChecked(True)
        self.dbf_create_groups.setStyleSheet("color: #c9d1d9; font-size: 13px;")

        self.dbf_create_levels = QCheckBox("Create discount levels from QUAN/PRICEM tiers")
        self.dbf_create_levels.setChecked(True)
        self.dbf_create_levels.setStyleSheet("color: #c9d1d9; font-size: 13px;")

        ol.addWidget(self.dbf_skip_dup)
        ol.addWidget(self.dbf_create_groups)
        ol.addWidget(self.dbf_create_levels)
        layout.addWidget(opt_frame)

        # ── Progress ──────────────────────────────────────────────────
        prog_frame = QFrame()
        prog_frame.setStyleSheet("background: #0a1929; border-radius: 8px;")
        pl = QVBoxLayout(prog_frame)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.setSpacing(8)

        self.dbf_progress = QProgressBar()
        self.dbf_progress.setRange(0, 100)
        self.dbf_progress.setValue(0)
        self.dbf_progress.setFixedHeight(10)
        self.dbf_progress.setTextVisible(False)
        self.dbf_progress.setStyleSheet("""
            QProgressBar {
                background: #172840; border: none; border-radius: 5px;
            }
            QProgressBar::chunk {
                background: #f59e0b; border-radius: 5px;
            }
        """)

        self.dbf_status_lbl = QLabel("Select a DBF file to begin.")
        self.dbf_status_lbl.setStyleSheet("color: #5a7a9a; font-size: 12px;")

        pl.addWidget(self.dbf_progress)
        pl.addWidget(self.dbf_status_lbl)
        layout.addWidget(prog_frame)

        # ── Log / results ─────────────────────────────────────────────
        log_frame = QFrame()
        log_frame.setStyleSheet("background: #0a1929; border-radius: 8px;")
        ll = QVBoxLayout(log_frame)
        ll.setContentsMargins(16, 14, 16, 14)
        ll.setSpacing(6)

        log_hdr = QHBoxLayout()
        log_lbl = QLabel("IMPORT LOG")
        log_lbl.setStyleSheet(_SECTION_LBL)
        clear_log_btn = QPushButton("Clear")
        clear_log_btn.setFixedHeight(24)
        clear_log_btn.setFixedWidth(60)
        clear_log_btn.setStyleSheet(_BTN_OUTLINE + "QPushButton { font-size: 11px; }")
        clear_log_btn.clicked.connect(lambda: self.dbf_log.clear())
        log_hdr.addWidget(log_lbl)
        log_hdr.addStretch()
        log_hdr.addWidget(clear_log_btn)
        ll.addLayout(log_hdr)

        self.dbf_log = QTextEdit()
        self.dbf_log.setReadOnly(True)
        self.dbf_log.setFixedHeight(180)
        self.dbf_log.setStyleSheet("""
            QTextEdit {
                background: #07111f; color: #94aac4;
                border: 1px solid #1e3a5f; border-radius: 6px;
                font-family: monospace; font-size: 12px;
                padding: 6px;
            }
        """)
        ll.addWidget(self.dbf_log)
        layout.addWidget(log_frame)

        # ── Import button ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self.dbf_import_btn = QPushButton("📥  Start Import")
        self.dbf_import_btn.setFixedHeight(42)
        self.dbf_import_btn.setFixedWidth(200)
        self.dbf_import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dbf_import_btn.setStyleSheet(_BTN_BLUE)
        self.dbf_import_btn.setEnabled(False)
        self.dbf_import_btn.clicked.connect(self._dbf_start_import)
        btn_row.addStretch()
        btn_row.addWidget(self.dbf_import_btn)
        layout.addLayout(btn_row)

        self._dbf_worker = None
        return w

    # ── DBF tab helpers ───────────────────────────────────────────────

    def _dbf_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select DBF File", "",
            "dBase Files (*.DBF *.dbf);;All Files (*)"
        )
        if not path:
            return
        self.dbf_path_edit.setText(path)
        self.dbf_import_btn.setEnabled(True)
        self.dbf_status_lbl.setText("Ready to import.")
        self.dbf_progress.setValue(0)
        # Quick preview: count records
        try:
            import sys, os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from import_stock_dbf import read_dbf
            _, records = read_dbf(path)
            self.dbf_preview_lbl.setText(
                f"  {len(records)} non-deleted records found in file."
            )
        except Exception as e:
            self.dbf_preview_lbl.setText(f"  Could not preview file: {e}")

    def _dbf_start_import(self):
        path = self.dbf_path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "No File", "Please select a DBF file first.")
            return

        import os
        if not os.path.exists(path):
            QMessageBox.warning(self, "File Not Found", f"Cannot find:\n{path}")
            return

        # Confirm
        reply = QMessageBox.question(
            self, "Confirm Import",
            f"Import products from:\n{path}\n\n"
            "This will add new products. Existing products with matching "
            "barcodes will be skipped. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from config import PRODUCTS_DB
        db_path = str(PRODUCTS_DB)

        self.dbf_import_btn.setEnabled(False)
        self.dbf_progress.setValue(5)
        self.dbf_status_lbl.setText("Starting import…")
        self.dbf_log.append(f"▶  Importing: {path}")

        opts = {
            "skip_dup":      self.dbf_skip_dup.isChecked(),
            "create_groups": self.dbf_create_groups.isChecked(),
            "create_levels": self.dbf_create_levels.isChecked(),
        }

        self._dbf_worker = _DbfImportWorker(path, db_path, opts)
        self._dbf_worker.progress.connect(self._dbf_on_progress)
        self._dbf_worker.log_line.connect(self._dbf_on_log)
        self._dbf_worker.finished.connect(self._dbf_on_finished)
        self._dbf_worker.start()

    def _dbf_on_progress(self, pct, msg):
        self.dbf_progress.setValue(pct)
        self.dbf_status_lbl.setText(msg)

    def _dbf_on_log(self, line):
        self.dbf_log.append(line)
        # Auto-scroll to bottom
        sb = self.dbf_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _dbf_on_finished(self, ok, summary):
        self.dbf_progress.setValue(100 if ok else 0)
        self.dbf_import_btn.setEnabled(True)
        self._dbf_worker = None
        if ok:
            self.dbf_status_lbl.setStyleSheet("color: #10d98a; font-size: 12px;")
            self.dbf_status_lbl.setText("✓  Import complete.")
            self.dbf_log.append("\n" + summary)
            QMessageBox.information(self, "Import Complete", summary)
        else:
            self.dbf_status_lbl.setStyleSheet("color: #f87171; font-size: 12px;")
            self.dbf_status_lbl.setText("✕  Import failed.")
            self.dbf_log.append(f"\n✕  FAILED: {summary}")
            QMessageBox.critical(self, "Import Failed", summary)

    # ================================================================
    # POSTGRESQL SYNC TAB
    # ================================================================

    def _build_sync_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #0d1f2d;")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # ── Connection settings ──────────────────────────────────────
        cfg_frame = QFrame()
        cfg_frame.setStyleSheet("background: #0b1120; border-radius: 8px;")
        cfg_l = QVBoxLayout(cfg_frame)
        cfg_l.setContentsMargins(20, 16, 20, 16)
        cfg_l.setSpacing(10)

        cfg_title = QLabel("POSTGRESQL CONNECTION")
        cfg_title.setStyleSheet(_SECTION_LBL)
        cfg_l.addWidget(cfg_title)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setStyleSheet(_DIVIDER)
        cfg_l.addWidget(sep)

        self.sync_enabled = QCheckBox("Enable PostgreSQL sync")
        self.sync_enabled.setStyleSheet("color: #94a3b8; font-size: 13px;")
        cfg_l.addWidget(self.sync_enabled)

        def cfg_row(label, widget):
            r = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(80)
            lbl.setStyleSheet("color: #94a3b8; font-size: 13px;")
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
        self.sync_cfg_status.setStyleSheet("color: #64748b; font-size: 11px;")
        self.sync_cfg_status.setWordWrap(True)
        cfg_l.addWidget(self.sync_cfg_status)

        # ── Sync actions ─────────────────────────────────────────────
        act_frame = QFrame()
        act_frame.setStyleSheet("background: #0b1120; border-radius: 8px;")
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
        desc.setStyleSheet("color: #64748b; font-size: 12px;")
        act_l.addWidget(desc)

        act_btn_row = QHBoxLayout()
        schema_btn = QPushButton("🔧  Mirror Schema")
        push_btn   = QPushButton("⬆  Push to Remote")
        pull_btn   = QPushButton("⬇  Pull from Remote")
        sync_btn   = QPushButton("🔄  Full Sync")

        for b, slot, bg in [
            (schema_btn, self._sync_schema,  "#1e293b"),
            (push_btn,   self._sync_push,    "#f59e0b"),
            (pull_btn,   self._sync_pull,    "#10b98122"),
            (sync_btn,   self._sync_full,    "#f59e0b"),
        ]:
            b.setFixedHeight(34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"QPushButton {{ background: {bg}; color: #fff; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; padding: 0 12px; }} QPushButton:hover {{ opacity: 0.85; }}")
            b.clicked.connect(slot)
            act_btn_row.addWidget(b)

        act_l.addLayout(act_btn_row)

        self.sync_result = QLabel("")
        self.sync_result.setWordWrap(True)
        self.sync_result.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: monospace;")
        act_l.addWidget(self.sync_result)

        # ── Sync log ──────────────────────────────────────────────────
        log_frame = QFrame()
        log_frame.setStyleSheet("background: #0b1120; border-radius: 8px;")
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
        self.sync_log_table.setMinimumHeight(120)
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
        import re
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
            self.sync_cfg_status.setStyleSheet("color: #10b981; font-size: 11px;")
            self.sync_cfg_status.setText("✓ Config saved. Restart required for USE_POSTGRES to take effect.")
        except Exception as e:
            self.sync_cfg_status.setStyleSheet("color: #ef4444; font-size: 11px;")
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
        color = "#10b981" if ok else "#ef4444"
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
        ec = {"push": "#4493f8", "pull": "#10b981", "error": "#ef4444",
              "test": "#a78bfa", "sync": "#f59e0b"}
        for i, e in enumerate(entries):
            ti = QTableWidgetItem(e["time"] or "")
            ti.setForeground(QColor("#64748b"))
            ev = QTableWidgetItem(e["event"] or "")
            ev.setForeground(QColor(ec.get(e["event"], "#94a3b8")))
            tb = QTableWidgetItem(e["table"] or "")
            ri = QTableWidgetItem(str(e["rows"] or ""))
            ri.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            mi = QTableWidgetItem(e["message"] or "")
            mi.setForeground(QColor("#64748b"))
            for col, item in enumerate([ti, ev, tb, ri, mi]):
                tbl.setItem(i, col, item)
            tbl.setRowHeight(i, 28)


# ──────────────────────────────────────────────────────────────────────────────
# DBF IMPORT WORKER  (runs in a background QThread)
# ──────────────────────────────────────────────────────────────────────────────

class _DbfImportWorker(QThread):
    """
    Runs import_stock_dbf.import_dbf in a background thread.
    Emits progress(pct, message), log_line(text), finished(ok, summary).
    """

    progress = pyqtSignal(int, str)
    log_line = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, dbf_path, db_path, opts, parent=None):
        super().__init__(parent)
        self._dbf_path = dbf_path
        self._db_path  = db_path
        self._opts     = opts

    def run(self):
        import sqlite3, os, sys

        # Ensure the project root is on sys.path so import_stock_dbf is importable
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        try:
            from import_stock_dbf import read_dbf, _float, _bool_dbf
        except ImportError as e:
            self.finished.emit(False, f"Cannot find import_stock_dbf.py: {e}")
            return

        try:
            # ── 1. Read DBF ──────────────────────────────────────────
            self.progress.emit(10, "Reading DBF file…")
            self.log_line.emit(f"  Reading: {self._dbf_path}")
            fields, records = read_dbf(self._dbf_path)
            total = len(records)
            self.log_line.emit(f"  {total} non-deleted records found.")
            if total == 0:
                self.finished.emit(False, "No records found in DBF file.")
                return

            # ── 2. Open DB ───────────────────────────────────────────
            self.progress.emit(15, "Opening database…")
            conn = sqlite3.connect(self._db_path)
            conn.execute("PRAGMA foreign_keys = ON")
            cur  = conn.cursor()

            # Ensure stock_qty column exists
            existing_cols = {r[1] for r in cur.execute("PRAGMA table_info(products)").fetchall()}
            if "stock_qty" not in existing_cols:
                cur.execute("ALTER TABLE products ADD COLUMN stock_qty REAL NOT NULL DEFAULT 0.0")
                conn.commit()
                self.log_line.emit("  Added stock_qty column to products table.")

            # ── 3. Product groups ────────────────────────────────────
            group_id_map = {}
            if self._opts.get("create_groups", True):
                self.progress.emit(20, "Creating product groups…")
                group_names = sorted({r["GROUP"] for r in records if r.get("GROUP", "").strip()})
                for gname in group_names:
                    cur.execute(
                        "INSERT OR IGNORE INTO product_groups (group_name, profit_percent) VALUES (?, 0.0)",
                        (gname,)
                    )
                    row = cur.execute(
                        "SELECT id FROM product_groups WHERE group_name = ?", (gname,)
                    ).fetchone()
                    group_id_map[gname] = row[0]
                conn.commit()
                self.log_line.emit(f"  Groups: {len(group_id_map)} created/found.")

            # ── 4. Discount levels ───────────────────────────────────
            disc_id_map = {}
            if self._opts.get("create_levels", True):
                self.progress.emit(30, "Building discount levels…")
                tier_set = set()
                for r in records:
                    sp = _float(r.get("PRICE", 0)) or _float(r.get("PRICEG", 0))
                    if sp <= 0:
                        continue
                    for q_field, p_field in [("QUAN1","PRICEM1"),("QUAN2","PRICEM2"),("QUAN3","PRICEM3")]:
                        qty   = _float(r.get(q_field, 0))
                        price = _float(r.get(p_field, 0))
                        if qty > 0 and 0 < price < sp:
                            pct = round((sp - price) / sp * 100, 1)
                            if pct > 0:
                                tier_set.add((int(qty), pct))
                for min_qty, pct in sorted(tier_set):
                    level_name = f"Buy {min_qty}+ ({pct:.2f}% off)"
                    cur.execute(
                        "INSERT OR IGNORE INTO discount_levels (level_name, min_quantity, discount_percent) VALUES (?,?,?)",
                        (level_name, min_qty, pct)
                    )
                    row = cur.execute(
                        "SELECT id FROM discount_levels WHERE level_name = ?", (level_name,)
                    ).fetchone()
                    disc_id_map[(min_qty, pct)] = row[0]
                conn.commit()
                self.log_line.emit(f"  Discount levels: {len(disc_id_map)} created/found.")

            # ── 5. Import products ───────────────────────────────────
            self.progress.emit(40, "Importing products…")
            inserted = 0
            skipped  = 0
            no_barcode = 0
            errors   = []

            for i, r in enumerate(records):
                # Progress update every 50 records
                if i % 50 == 0:
                    pct = 40 + int((i / total) * 55)
                    self.progress.emit(pct, f"Importing… {i}/{total}")

                barcode = r.get("CODE", "").strip()
                if not barcode:
                    no_barcode += 1
                    continue

                name          = r.get("DESCRIP", "").strip() or "(no name)"
                brand         = r.get("CATEGORY", "").strip() or None
                selling_price = _float(r.get("PRICE", 0)) or _float(r.get("PRICEG", 0))
                cost          = _float(r.get("COST", 0))
                gct           = _bool_dbf(r.get("GCT", ""))
                stock_qty     = _float(r.get("QUANTITY", 0))
                group_id      = group_id_map.get(r.get("GROUP", "")) if r.get("GROUP", "").strip() else None

                def resolve_tier(q_field, p_field):
                    sp = selling_price
                    if sp <= 0:
                        return None
                    qty   = _float(r.get(q_field, 0))
                    price = _float(r.get(p_field, 0))
                    if qty > 0 and 0 < price < sp:
                        pct = round((sp - price) / sp * 100, 1)
                        return disc_id_map.get((int(qty), pct))
                    return None

                disc1 = resolve_tier("QUAN1", "PRICEM1")
                disc2 = resolve_tier("QUAN2", "PRICEM2")
                if disc2 == disc1:
                    disc2 = None

                try:
                    cur.execute("""
                        INSERT INTO products
                            (barcode, brand, name, cost, selling_price,
                             gct_applicable, stock_qty, group_id,
                             discount_level, discount_level_2,
                             is_case, case_quantity)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
                    """, (barcode, brand, name, cost, selling_price,
                          gct, stock_qty, group_id, disc1, disc2))
                    inserted += 1
                except sqlite3.IntegrityError:
                    if self._opts.get("skip_dup", True):
                        skipped += 1
                        errors.append(f"  SKIP: {barcode}  {name}")
                    else:
                        # Overwrite
                        cur.execute("""
                            UPDATE products SET brand=?, name=?, cost=?, selling_price=?,
                                gct_applicable=?, stock_qty=?, group_id=?,
                                discount_level=?, discount_level_2=?
                            WHERE barcode=?
                        """, (brand, name, cost, selling_price, gct, stock_qty,
                              group_id, disc1, disc2, barcode))
                        inserted += 1

            conn.commit()
            conn.close()

            # ── 6. Summary ───────────────────────────────────────────
            self.progress.emit(100, "Done.")
            summary_lines = [
                f"✓  Inserted:        {inserted}",
                f"⚠  Skipped (dup):   {skipped}",
                f"⚠  No barcode:      {no_barcode}",
            ]
            if errors:
                summary_lines.append(f"\nFirst {min(len(errors),10)} skipped barcodes:")
                summary_lines += errors[:10]
                if len(errors) > 10:
                    summary_lines.append(f"  … and {len(errors)-10} more")

            for line in summary_lines:
                self.log_line.emit(line)

            summary_short = (
                f"Import complete.\n\n"
                f"  Inserted:      {inserted}\n"
                f"  Skipped (dup): {skipped}\n"
                f"  No barcode:    {no_barcode}"
            )
            self.finished.emit(True, summary_short)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.log_line.emit(f"\n✕  Error:\n{tb}")
            self.finished.emit(False, str(e))
