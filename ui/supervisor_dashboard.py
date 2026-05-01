"""
ui/supervisor_dashboard.py
Supervisor dashboard with tabbed interface.
Tabs: Products | Reports | Transactions | Void / Refund
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QCheckBox, QAbstractItemView,
    QMessageBox, QScrollArea, QSizePolicy, QFormLayout, QCompleter,
    QSplitter, QTreeWidget, QTreeWidgetItem, QSpinBox, QListWidget,
    QListWidgetItem, QRadioButton, QButtonGroup, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, QStringListModel, QRectF, QSizeF, QMarginsF
from PyQt6.QtGui import (
    QColor, QDoubleValidator, QIntValidator, QPainter, QFont,
    QFontMetrics, QPen, QBrush, QPageSize, QPageLayout
)
from ui.base_window import BaseWindow
from db import get_products_conn, get_users_conn, get_transactions_conn, get_business_conn, recalculate_selling_prices


class SupervisorDashboard(BaseWindow):

    def __init__(self, user_id, full_name, role="supervisor"):
        super().__init__()
        self.user_id   = user_id
        self.full_name = full_name
        self.role      = role
        self.editing_product_id = None  # None = add mode, int = edit mode

        self.setWindowTitle("POS System — Supervisor")
        self.setMinimumSize(1280, 720)
        self._center_on_screen()
        self._build_ui()

        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

    # ----------------------------------------------------------------
    # UI CONSTRUCTION
    # ----------------------------------------------------------------

    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet("background-color: #0d1117;")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        layout.addWidget(self._build_topbar())
        layout.addWidget(self._build_tabs(), stretch=1)

    # ── Top bar ──────────────────────────────────────────────────────
    def _build_topbar(self):
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet("background-color: #1a56db; border-radius: 10px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        left = QLabel(f"POS System  |  Supervisor:  {self.full_name}")
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

    # ── Tabs ─────────────────────────────────────────────────────────
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

        self.tabs.addTab(self._build_products_tab(),      "Products")
        self.tabs.addTab(self._build_reports_tab(),       "Reports")
        self.tabs.addTab(self._build_transactions_tab(),  "Transactions")
        self.tabs.addTab(self._build_void_tab(),          "Void / Refund")
        self.tabs.addTab(self._build_labels_tab(),        "🏷  Labels")
        self.tabs.setCurrentIndex(0)
        return self.tabs

    # ── Reports tab — stub ───────────────────────────────────────────
    # ================================================================
    # REPORTS TAB — Cashing Sessions
    # ================================================================

    def _build_reports_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        _btn_outline = """
            QPushButton {
                background: transparent; color: #c9d1d9;
                border: 1.5px solid #30363d; border-radius: 17px;
                font-size: 12px; font-weight: 600; padding: 0 14px;
            }
            QPushButton:hover  { background: #21262d; color: #ffffff; }
            QPushButton:pressed{ background: #30363d; }
            QPushButton:disabled{ color: #3d444d; border-color: #21262d; }
        """
        _btn_red = """
            QPushButton {
                background: #7f1d1d; color: #fca5a5;
                border: none; border-radius: 17px;
                font-size: 12px; font-weight: 600; padding: 0 14px;
            }
            QPushButton:hover  { background: #991b1b; }
            QPushButton:pressed{ background: #b91c1c; }
            QPushButton:disabled{ background: #2d1515; color: #6b3030; }
        """
        _btn_green = """
            QPushButton {
                background: #14532d; color: #86efac;
                border: none; border-radius: 17px;
                font-size: 12px; font-weight: 600; padding: 0 14px;
            }
            QPushButton:hover  { background: #166534; }
            QPushButton:pressed{ background: #15803d; }
        """

        # ── Left panel: cashier list ─────────────────────────────────
        left = QFrame()
        left.setFixedWidth(265)
        left.setStyleSheet("background: #0d1117; border-radius: 8px;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        lbl_cashiers = QLabel("CASHIERS")
        lbl_cashiers.setStyleSheet("color: #8b949e; font-size: 10px; font-weight: 700; letter-spacing: 1px;")

        self.rpt_cashier_search = QLineEdit()
        self.rpt_cashier_search.setPlaceholderText("\U0001f50d  Search cashier\u2026")
        self.rpt_cashier_search.setFixedHeight(34)
        self.rpt_cashier_search.setStyleSheet("""
            QLineEdit {
                background-color: #161b22; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 17px;
                padding: 0 12px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #1a56db; }
        """)
        self.rpt_cashier_search.textChanged.connect(self._rpt_filter_cashiers)

        self.rpt_cashier_list = QTableWidget()
        self.rpt_cashier_list.setColumnCount(1)
        self.rpt_cashier_list.setHorizontalHeaderLabels(["Name"])
        self.rpt_cashier_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.rpt_cashier_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rpt_cashier_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rpt_cashier_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.rpt_cashier_list.verticalHeader().setVisible(False)
        self.rpt_cashier_list.setShowGrid(False)
        self.rpt_cashier_list.setStyleSheet("""
            QTableWidget { background: transparent; color: #c9d1d9; border: none; font-size: 12px; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #21262d; }
            QTableWidget::item:selected { background-color: #1a56db33; color: #ffffff; border-left: 3px solid #1a56db; }
            QHeaderView::section { background: #0d1117; color: #8b949e; border: none;
                                   padding: 6px 8px; font-size: 11px; font-weight: 700;
                                   border-bottom: 1px solid #21262d; }
        """)
        self.rpt_cashier_list.selectionModel().selectionChanged.connect(self._rpt_on_cashier_selected)

        left_layout.addWidget(lbl_cashiers)
        left_layout.addWidget(self.rpt_cashier_search)
        left_layout.addWidget(self.rpt_cashier_list, stretch=1)

        # ── Right panel ──────────────────────────────────────────────
        right = QFrame()
        right.setStyleSheet("background: #0d1117; border-radius: 8px;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        # Summary cards
        cards_row = QHBoxLayout()
        self.rpt_cards = {}
        for key, label, color in [
            ("total_sales",  "TOTAL SALES",   "#3dd68c"),
            ("total_gct",    "TOTAL GCT",     "#3dd68c"),
            ("transactions", "TRANSACTIONS",  "#a78bfa"),
            ("discounts",    "DISCOUNTS",     "#f59e0b"),
        ]:
            card = QFrame()
            card.setFixedHeight(72)
            card.setStyleSheet("background: #161b22; border-radius: 8px;")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 8, 14, 8)
            cl.setSpacing(2)
            t = QLabel(label)
            t.setStyleSheet("color: #8b949e; font-size: 10px; font-weight: 700;")
            v = QLabel("\u2014")
            v.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: 700;")
            cl.addWidget(t)
            cl.addWidget(v)
            self.rpt_cards[key] = v
            cards_row.addWidget(card)
        right_layout.addLayout(cards_row)

        # Session bar
        session_bar = QHBoxLayout()
        session_bar.setSpacing(8)

        self.rpt_session_header = QLabel("Select a cashier to view sessions")
        self.rpt_session_header.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 700;")

        self.rpt_search_bar = QLineEdit()
        self.rpt_search_bar.setPlaceholderText("\U0001f50d  Date or session #\u2026")
        self.rpt_search_bar.setFixedHeight(34)
        self.rpt_search_bar.setFixedWidth(200)
        self.rpt_search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #161b22; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 17px;
                padding: 0 12px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #1a56db; }
        """)
        self.rpt_search_bar.textChanged.connect(self._rpt_filter_sessions)

        self.rpt_refresh_btn = QPushButton("\u21bb  Refresh")
        self.rpt_refresh_btn.setFixedHeight(34)
        self.rpt_refresh_btn.setStyleSheet(_btn_outline)
        self.rpt_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rpt_refresh_btn.clicked.connect(self._rpt_refresh)

        self.rpt_close_btn = QPushButton("Close Session")
        self.rpt_close_btn.setFixedHeight(34)
        self.rpt_close_btn.setStyleSheet(_btn_red)
        self.rpt_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rpt_close_btn.setEnabled(False)
        self.rpt_close_btn.clicked.connect(self._rpt_close_session)

        self.rpt_open_btn = QPushButton("Open New Session")
        self.rpt_open_btn.setFixedHeight(34)
        self.rpt_open_btn.setStyleSheet(_btn_green)
        self.rpt_open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rpt_open_btn.setEnabled(False)          # enabled once a cashier is selected
        self.rpt_open_btn.clicked.connect(self._rpt_open_session)

        self.rpt_print_btn = QPushButton("Print Summary")
        self.rpt_print_btn.setFixedHeight(34)
        self.rpt_print_btn.setStyleSheet(_btn_outline)
        self.rpt_print_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rpt_print_btn.setEnabled(False)
        self.rpt_print_btn.clicked.connect(self._rpt_print_session)

        session_bar.addWidget(self.rpt_session_header)
        session_bar.addStretch()
        session_bar.addWidget(self.rpt_search_bar)
        session_bar.addWidget(self.rpt_refresh_btn)
        session_bar.addWidget(self.rpt_close_btn)
        session_bar.addWidget(self.rpt_open_btn)
        session_bar.addWidget(self.rpt_print_btn)
        right_layout.addLayout(session_bar)

        # Session list
        self.rpt_session_list = QTableWidget()
        self.rpt_session_list.setColumnCount(5)
        self.rpt_session_list.setHorizontalHeaderLabels(["Session", "Status", "Opened", "Closed", "Sales"])
        self.rpt_session_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.rpt_session_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.rpt_session_list.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.rpt_session_list.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.rpt_session_list.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.rpt_session_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rpt_session_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rpt_session_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.rpt_session_list.verticalHeader().setVisible(False)
        self.rpt_session_list.setShowGrid(False)
        self.rpt_session_list.setStyleSheet("""
            QTableWidget { background: transparent; color: #c9d1d9; border: none; font-size: 12px; }
            QTableWidget::item { padding: 10px 8px; border-bottom: 1px solid #21262d; }
            QTableWidget::item:selected { background-color: #1a56db33; color: #ffffff; }
            QHeaderView::section { background: #0d1117; color: #8b949e; border: none; padding: 8px;
                                   font-size: 11px; font-weight: 700; border-bottom: 1px solid #21262d; }
        """)
        self.rpt_session_list.selectionModel().selectionChanged.connect(self._rpt_on_session_selected)

        right_layout.addWidget(self.rpt_session_list, stretch=1)

        layout.addWidget(left)
        layout.addWidget(right, stretch=1)

        self._rpt_all_cashiers        = []
        self._rpt_all_sessions        = []
        self._rpt_selected_cashier_id   = None
        self._rpt_selected_cashier_name = None
        self._rpt_selected_session_id = None

        self._rpt_load_cashiers()
        return w

    # ── Reports: data loaders ────────────────────────────────────────

    def _rpt_load_cashiers(self):
        """Load all cashiers for the left panel.

        Sources (merged by cashier_id, deduplicated):
          1. Active cashiers from users.db (role='cashier')
          2. Historical cashiers recorded in the sessions table
             (covers deleted / role-changed users who still have history)

        The 'has_open' flag lights up (green dot) when the cashier has an
        open CASHING session — meaning they are cleared to operate the till.
        """
        cashiers: dict = {}

        # ── Source 1: active cashiers from users.db ──────────────────
        try:
            conn_u = get_users_conn()
            for r in conn_u.execute(
                "SELECT id, full_name FROM users "
                "WHERE role='cashier' AND is_active=1 ORDER BY full_name"
            ).fetchall():
                cashiers[r[0]] = {
                    "cashier_id":   r[0],
                    "cashier_name": r[1],
                    "total_sales":  0.0,
                    "has_open":     0,
                }
            conn_u.close()
        except Exception:
            pass

        # ── Source 2: historical cashiers from sessions table ─────────
        try:
            conn_t = get_transactions_conn()
            for r in conn_t.execute("""
                SELECT cashier_id, cashier_name, SUM(total_sales)
                FROM sessions
                GROUP BY cashier_id, cashier_name
                ORDER BY cashier_name
            """).fetchall():
                if r[0] not in cashiers:
                    cashiers[r[0]] = {
                        "cashier_id":   r[0],
                        "cashier_name": r[1],
                        "total_sales":  r[2] or 0.0,
                        "has_open":     0,
                    }
            conn_t.close()
        except Exception:
            pass

        # ── Source 3: which cashiers have an open cashing session ─────
        open_cashing: set = set()
        try:
            conn_t2 = get_transactions_conn()
            for r in conn_t2.execute(
                "SELECT cashier_id FROM cashing_sessions "
                "WHERE status='open' AND cashier_id IS NOT NULL"
            ).fetchall():
                open_cashing.add(r[0])
            conn_t2.close()
        except Exception:
            pass

        for c in cashiers.values():
            c["has_open"] = 1 if c["cashier_id"] in open_cashing else 0

        self._rpt_all_cashiers = sorted(
            cashiers.values(), key=lambda c: c["cashier_name"]
        )
        self._rpt_populate_cashier_list(self._rpt_all_cashiers)

    def _rpt_populate_cashier_list(self, cashiers):
        tbl = self.rpt_cashier_list
        tbl.setRowCount(len(cashiers))
        for row, c in enumerate(cashiers):
            has_open = bool(c.get("has_open"))
            display_name = ("● " if has_open else "") + c["cashier_name"]
            name_item = QTableWidgetItem(display_name)
            name_item.setData(Qt.ItemDataRole.UserRole, c["cashier_id"])
            name_item.setForeground(QColor("#3dd68c" if has_open else "#c9d1d9"))
            tbl.setItem(row, 0, name_item)
        tbl.resizeRowsToContents()

    def _rpt_filter_cashiers(self, text):
        q = text.lower()
        filtered = [c for c in self._rpt_all_cashiers
                    if q in c["cashier_name"].lower()]
        self._rpt_populate_cashier_list(filtered)

    def _rpt_on_cashier_selected(self):
        sel = self.rpt_cashier_list.selectedItems()
        if not sel:
            return
        row = self.rpt_cashier_list.currentRow()
        item = self.rpt_cashier_list.item(row, 0)
        cashier_id = item.data(Qt.ItemDataRole.UserRole)
        # Strip the leading bullet if present
        cashier_name = item.text().lstrip("● ").strip()
        self._rpt_selected_cashier_id = cashier_id
        self._rpt_selected_cashier_name = cashier_name
        self._rpt_selected_session_id = None
        self.rpt_session_header.setText(f"Sessions  —  {cashier_name}")
        self.rpt_open_btn.setEnabled(True)
        self._rpt_load_sessions(cashier_id)
        self._rpt_update_cards()

    def _rpt_load_sessions(self, cashier_id):
        """Load cashing sessions for the selected cashier."""
        try:
            conn = get_transactions_conn()
            rows = conn.execute("""
                SELECT id, status, opened_at, closed_at, total_sales,
                       total_gct, total_discount, transaction_count
                FROM cashing_sessions
                WHERE cashier_id = ?
                ORDER BY id DESC
            """, (cashier_id,)).fetchall()
            conn.close()
        except Exception:
            rows = []

        self._rpt_all_sessions = [
            {"id": r[0], "status": r[1], "opened_at": r[2],
             "closed_at": r[3], "total_sales": r[4] or 0.0,
             "total_gct": r[5] or 0.0, "total_discount": r[6] or 0.0,
             "transaction_count": r[7] or 0}
            for r in rows
        ]
        self._rpt_populate_session_list(self._rpt_all_sessions)
        self._rpt_update_cards()

    def _rpt_populate_session_list(self, sessions):
        tbl = self.rpt_session_list
        tbl.setRowCount(len(sessions))
        for row, s in enumerate(sessions):
            num_item = QTableWidgetItem(f"Session #{s['id']}")
            num_item.setData(Qt.ItemDataRole.UserRole, s["id"])
            num_item.setForeground(QColor("#ffffff"))
            num_item.setFont(num_item.font())

            is_open = s["status"] == "open"
            status_item = QTableWidgetItem("  Open  " if is_open else "  Closed  ")
            status_item.setForeground(QColor("#3dd68c" if is_open else "#8b949e"))
            status_item.setBackground(QColor("#14532d" if is_open else "#21262d"))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            opened = self._fmt_dt(s["opened_at"])
            closed = self._fmt_dt(s["closed_at"]) if s["closed_at"] else "—"
            opened_item = QTableWidgetItem(opened)
            closed_item = QTableWidgetItem(closed)
            opened_item.setForeground(QColor("#8b949e"))
            closed_item.setForeground(QColor("#8b949e"))

            sales_item = QTableWidgetItem(f"$ {s['total_sales']:,.2f}")
            sales_item.setForeground(QColor("#3dd68c"))
            sales_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            tbl.setItem(row, 0, num_item)
            tbl.setItem(row, 1, status_item)
            tbl.setItem(row, 2, opened_item)
            tbl.setItem(row, 3, closed_item)
            tbl.setItem(row, 4, sales_item)
        tbl.resizeRowsToContents()

    def _rpt_filter_sessions(self, text):
        q = text.lower()
        filtered = [s for s in self._rpt_all_sessions
                    if q in str(s["id"]) or
                       q in (s["opened_at"] or "").lower() or
                       q in (s["closed_at"] or "").lower()]
        self._rpt_populate_session_list(filtered)

    def _rpt_on_session_selected(self):
        row = self.rpt_session_list.currentRow()
        item = self.rpt_session_list.item(row, 0)
        if not item:
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        self._rpt_selected_session_id = session_id
        # Find session data
        sess = next((s for s in self._rpt_all_sessions if s["id"] == session_id), None)
        if sess:
            self.rpt_cards["total_sales"].setText(f"${sess['total_sales']:,.2f}")
            self.rpt_cards["total_gct"].setText(f"${sess['total_gct']:,.2f}")
            self.rpt_cards["transactions"].setText(str(sess["transaction_count"]))
            self.rpt_cards["discounts"].setText(f"${sess['total_discount']:,.2f}")
            is_open = sess["status"] == "open"
            self.rpt_close_btn.setEnabled(is_open)
            self.rpt_print_btn.setEnabled(True)

    def _rpt_update_cards(self):
        """Reset cards to dash — cards are only populated when a session row is selected."""
        for k in self.rpt_cards:
            self.rpt_cards[k].setText("—")
        self.rpt_close_btn.setEnabled(False)
        self.rpt_print_btn.setEnabled(False)

    # ── Reports: actions ─────────────────────────────────────────────

    def _rpt_refresh(self):
        """Reload cashier list; if a cashier is selected reload their sessions too."""
        self._rpt_load_cashiers()
        if self._rpt_selected_cashier_id is not None:
            self._rpt_load_sessions(self._rpt_selected_cashier_id)

    def _rpt_print_session(self):
        """Print summary for the selected session."""
        if not hasattr(self, "_rpt_selected_session_id") or not self._rpt_selected_session_id:
            QMessageBox.information(self, "No Session", "Please select a session first.")
            return
        try:
            from printing.print_manager import print_session
            ok, err = print_session(self._rpt_selected_session_id, parent=self)
            if not ok and err and err != "Cancelled":
                QMessageBox.warning(self, "Print Failed", err)
        except Exception as e:
            QMessageBox.critical(self, "Print Error", str(e))

    def _rpt_open_session(self):
        # Must have a cashier selected
        if self._rpt_selected_cashier_id is None:
            QMessageBox.warning(self, "No Cashier Selected",
                                "Select a cashier from the left panel first.")
            return

        cashier_id   = self._rpt_selected_cashier_id
        cashier_name = getattr(self, "_rpt_selected_cashier_name",
                               str(cashier_id))

        # Warn if they already have an open session
        try:
            conn_chk = get_transactions_conn()
            existing = conn_chk.execute(
                "SELECT id FROM cashing_sessions "
                "WHERE cashier_id=? AND status='open' LIMIT 1",
                (cashier_id,)
            ).fetchone()
            conn_chk.close()
        except Exception:
            existing = None

        if existing:
            reply = QMessageBox.question(
                self, "Session Already Open",
                f"{cashier_name} already has an open session (#{existing[0]}).\n"
                "Open an additional session anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        else:
            reply = QMessageBox.question(
                self, "Open Session",
                f"Open a new cashing session for {cashier_name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            conn = get_transactions_conn()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT INTO cashing_sessions
                    (cashier_id, cashier_name,
                     opened_by_id, opened_by_name, opened_at, status)
                VALUES (?, ?, ?, ?, ?, 'open')
            """, (cashier_id, cashier_name,
                  self.user_id, self.full_name, now))
            conn.commit()
            conn.close()
            QMessageBox.information(
                self, "Session Opened",
                f"New cashing session opened for {cashier_name}."
            )
            self._rpt_load_cashiers()
            self._rpt_load_sessions(cashier_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _rpt_close_session(self):
        if self._rpt_selected_session_id is None:
            return
        reply = QMessageBox.question(
            self, "Close Session",
            f"Close Session #{self._rpt_selected_session_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            conn = get_transactions_conn()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                UPDATE cashing_sessions
                SET status='closed', closed_at=?, closed_by_id=?, closed_by_name=?
                WHERE id=? AND status='open'
            """, (now, self.user_id, self.full_name, self._rpt_selected_session_id))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Session Closed", "Cashing session closed.")
            self._rpt_load_cashiers()
            if self._rpt_selected_cashier_id is not None:
                self._rpt_load_sessions(self._rpt_selected_cashier_id)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _fmt_dt(self, dt_str):
        """Format a datetime string nicely."""
        if not dt_str:
            return "—"
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%b %d, %Y  %I:%M %p")
        except Exception:
            return dt_str

    # ================================================================
    # TRANSACTIONS TAB
    # ================================================================

    def _build_transactions_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── Search bar row ───────────────────────────────────────────
        search_row = QHBoxLayout()

        self.tx_search = QLineEdit()
        self.tx_search.setPlaceholderText("🔍  Search by receipt #, cashier, date (YYYY-MM-DD)…")
        self.tx_search.setFixedHeight(36)
        self.tx_search.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 18px;
                padding: 0 16px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #1a56db; }
        """)
        self.tx_search.returnPressed.connect(self._tx_search)

        self.tx_status_filter = QComboBox()
        self.tx_status_filter.addItems(["All Statuses", "Completed", "Voided", "Refunded"])
        self.tx_status_filter.setFixedHeight(36)
        self.tx_status_filter.setFixedWidth(150)
        self.tx_status_filter.setStyleSheet("""
            QComboBox {
                background-color: #0d1117; color: #c9d1d9;
                border: 1.5px solid #30363d; border-radius: 18px;
                padding: 0 12px; font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; }
        """)
        self.tx_status_filter.currentIndexChanged.connect(lambda: None)  # no auto-search; use Search button

        btn_search = QPushButton("Search")
        btn_search.setFixedHeight(36)
        btn_search.setFixedWidth(90)
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.setStyleSheet("""
            QPushButton {
                background-color: #1a56db; color: #ffffff;
                border: none; border-radius: 18px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: #1e40af; }
        """)
        btn_search.clicked.connect(self._tx_search)

        _tx_btn_outline = """
            QPushButton {
                background: transparent; color: #c9d1d9;
                border: 1.5px solid #30363d; border-radius: 18px;
                font-size: 12px; font-weight: 600; padding: 0 14px;
            }
            QPushButton:hover  { background: #21262d; color: #ffffff; }
            QPushButton:pressed{ background: #30363d; }
            QPushButton:disabled{ color: #3d444d; border-color: #21262d; }
        """

        self.tx_refresh_btn = QPushButton("↻  Refresh")
        self.tx_refresh_btn.setFixedHeight(36)
        self.tx_refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tx_refresh_btn.setStyleSheet(_tx_btn_outline)
        self.tx_refresh_btn.clicked.connect(self._tx_search)

        self.tx_reprint_btn = QPushButton("🖨  Reprint")
        self.tx_reprint_btn.setFixedHeight(36)
        self.tx_reprint_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tx_reprint_btn.setStyleSheet(_tx_btn_outline)
        self.tx_reprint_btn.setEnabled(False)
        self.tx_reprint_btn.clicked.connect(self._tx_reprint)

        search_row.addWidget(self.tx_search, stretch=1)
        search_row.addWidget(self.tx_status_filter)
        search_row.addWidget(btn_search)
        search_row.addWidget(self.tx_refresh_btn)
        search_row.addWidget(self.tx_reprint_btn)
        layout.addLayout(search_row)

        # ── Split: transaction list | detail panel ───────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #30363d; width: 1px; }")

        # Left: transaction table
        left = QFrame()
        left.setStyleSheet("background: #0d1117; border-radius: 8px;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)

        self.tx_table = QTableWidget()
        self.tx_table.setColumnCount(6)
        self.tx_table.setHorizontalHeaderLabels(["Receipt #", "Cashier", "Date", "Time", "Total", "Status"])
        self.tx_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tx_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tx_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tx_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tx_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tx_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.tx_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tx_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tx_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tx_table.verticalHeader().setVisible(False)
        self.tx_table.setShowGrid(False)
        self.tx_table.setStyleSheet("""
            QTableWidget { background: transparent; color: #c9d1d9; border: none; font-size: 12px; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #21262d; }
            QTableWidget::item:selected { background-color: #1a56db22; color: #ffffff; }
            QHeaderView::section { background: #0d1117; color: #8b949e; border: none; padding: 8px;
                                   font-size: 11px; font-weight: 700; border-bottom: 1px solid #21262d; }
        """)
        self.tx_table.selectionModel().selectionChanged.connect(self._tx_on_row_selected)
        ll.addWidget(self.tx_table)

        # Right: detail panel
        right = QFrame()
        right.setFixedWidth(320)
        right.setStyleSheet("background: #0d1117; border-radius: 8px;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 14, 14, 14)
        rl.setSpacing(8)

        self.tx_detail_title = QLabel("Select a transaction")
        self.tx_detail_title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 700;")
        self.tx_detail_meta = QLabel("")
        self.tx_detail_meta.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.tx_detail_meta.setWordWrap(True)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #30363d;")

        self.tx_items_table = QTableWidget()
        self.tx_items_table.setColumnCount(4)
        self.tx_items_table.setHorizontalHeaderLabels(["Item", "Qty", "Price", "Total"])
        self.tx_items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tx_items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tx_items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tx_items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tx_items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tx_items_table.verticalHeader().setVisible(False)
        self.tx_items_table.setShowGrid(False)
        self.tx_items_table.setStyleSheet("""
            QTableWidget { background: transparent; color: #c9d1d9; border: none; font-size: 11px; }
            QTableWidget::item { padding: 5px 4px; border-bottom: 1px solid #21262d; }
            QHeaderView::section { background: #0d1117; color: #8b949e; border: none; padding: 5px;
                                   font-size: 10px; font-weight: 700; border-bottom: 1px solid #21262d; }
        """)

        # Totals footer
        self.tx_footer = QLabel("")
        self.tx_footer.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        self.tx_footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.tx_footer.setWordWrap(True)

        rl.addWidget(self.tx_detail_title)
        rl.addWidget(self.tx_detail_meta)
        rl.addWidget(sep)
        rl.addWidget(self.tx_items_table, stretch=1)
        rl.addWidget(self.tx_footer)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        layout.addWidget(splitter, stretch=1)

        # Load recent transactions on open
        self._tx_load(limit=100)
        return w

    # ── Transactions: data & actions ─────────────────────────────────

    def _tx_load(self, query="", status_filter="", limit=100):
        try:
            conn = get_transactions_conn()
            sql = """
                SELECT id, cashier_name, date, time, total, status
                FROM transactions
                WHERE 1=1
            """
            params = []
            if query:
                sql += " AND (CAST(id AS TEXT) LIKE ? OR LOWER(cashier_name) LIKE ? OR date LIKE ?)"
                q = f"%{query.lower()}%"
                params += [q, q, q]
            if status_filter and status_filter != "all":
                sql += " AND status = ?"
                params.append(status_filter)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            conn.close()
        except Exception:
            rows = []

        tbl = self.tx_table
        tbl.setRowCount(len(rows))
        status_colors = {"completed": "#3dd68c", "voided": "#f87171", "refunded": "#f59e0b"}
        for row, r in enumerate(rows):
            id_item = QTableWidgetItem(f"#{r[0]}")
            id_item.setData(Qt.ItemDataRole.UserRole, r[0])
            id_item.setForeground(QColor("#ffffff"))
            cashier_item = QTableWidgetItem(r[1])
            date_item = QTableWidgetItem(r[2])
            time_item = QTableWidgetItem(r[3])
            total_item = QTableWidgetItem(f"${r[4]:,.2f}")
            total_item.setForeground(QColor("#3dd68c"))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            status_text = r[5].capitalize()
            status_item = QTableWidgetItem(f"  {status_text}  ")
            status_item.setForeground(QColor(status_colors.get(r[5], "#8b949e")))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            for col, item in enumerate([id_item, cashier_item, date_item, time_item, total_item, status_item]):
                tbl.setItem(row, col, item)
        tbl.resizeRowsToContents()

    def _tx_search(self):
        query = self.tx_search.text().strip()
        status_map = {"All Statuses": "", "Completed": "completed",
                      "Voided": "voided", "Refunded": "refunded"}
        status = status_map.get(self.tx_status_filter.currentText(), "")
        self._tx_load(query=query, status_filter=status)

    def _tx_on_row_selected(self):
        row = self.tx_table.currentRow()
        item = self.tx_table.item(row, 0)
        if not item:
            return
        tx_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            conn = get_transactions_conn()
            tx = conn.execute(
                "SELECT id, cashier_name, date, time, subtotal, tax_amount, total, status FROM transactions WHERE id=?",
                (tx_id,)
            ).fetchone()
            items = conn.execute(
                "SELECT product_name_snapshot, quantity, unit_price_snapshot, discount_applied, line_total FROM transaction_items WHERE transaction_id=?",
                (tx_id,)
            ).fetchall()
            conn.close()
        except Exception:
            return
        if not tx:
            return

        self.tx_detail_title.setText(f"Receipt #{tx[0]}")
        self.tx_detail_meta.setText(
            f"Cashier: {tx[1]}\n"
            f"Date: {tx[2]}  {tx[3]}\n"
            f"Status: {tx[7].capitalize()}"
        )

        self.tx_items_table.setRowCount(len(items))
        for r, it in enumerate(items):
            name_item = QTableWidgetItem(it[0])
            qty_item  = QTableWidgetItem(str(it[1]))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            price_item = QTableWidgetItem(f"${it[2]:,.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            total_item = QTableWidgetItem(f"${it[4]:,.2f}")
            total_item.setForeground(QColor("#3dd68c"))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            for col, ci in enumerate([name_item, qty_item, price_item, total_item]):
                self.tx_items_table.setItem(r, col, ci)
        self.tx_items_table.resizeRowsToContents()

        self.tx_footer.setText(
            f"Subtotal:  ${tx[4]:,.2f}\n"
            f"GCT:        ${tx[5]:,.2f}\n"
            f"<b>Total:      ${tx[6]:,.2f}</b>"
        )
        self.tx_footer.setTextFormat(Qt.TextFormat.RichText)
        self.tx_reprint_btn.setEnabled(True)

    def _tx_reprint(self):
        """Reprint the selected receipt via the print manager."""
        row = self.tx_table.currentRow()
        item = self.tx_table.item(row, 0)
        if not item:
            return
        tx_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            from printing.print_manager import reprint_receipt
            ok, err = reprint_receipt(tx_id, parent=self)
            if not ok and err and err != "Cancelled":
                QMessageBox.warning(self, "Reprint Failed", err)
        except Exception as e:
            QMessageBox.critical(self, "Reprint Error", str(e))

    # ================================================================
    # VOID / REFUND TAB — stub
    # ================================================================

    # ================================================================
    # VOID / REFUND TAB
    # ================================================================

    def _build_void_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ── Shared button styles ─────────────────────────────────────
        self._vr_btn_outline = """
            QPushButton {
                background: transparent; color: #c9d1d9;
                border: 1.5px solid #30363d; border-radius: 17px;
                font-size: 12px; font-weight: 600; padding: 0 14px;
            }
            QPushButton:hover  { background: #21262d; color: #ffffff; }
            QPushButton:pressed{ background: #30363d; }
            QPushButton:disabled{ color: #3d444d; border-color: #21262d; }
        """
        self._vr_btn_red = """
            QPushButton {
                background: #7f1d1d; color: #fca5a5;
                border: none; border-radius: 17px;
                font-size: 12px; font-weight: 600; padding: 0 18px;
            }
            QPushButton:hover  { background: #991b1b; }
            QPushButton:pressed{ background: #b91c1c; }
            QPushButton:disabled{ background: #2d1515; color: #6b3030; }
        """
        self._vr_btn_amber = """
            QPushButton {
                background: #78350f; color: #fcd34d;
                border: none; border-radius: 17px;
                font-size: 12px; font-weight: 600; padding: 0 18px;
            }
            QPushButton:hover  { background: #92400e; }
            QPushButton:pressed{ background: #b45309; }
            QPushButton:disabled{ background: #2d1e05; color: #6b5010; }
        """

        # ── Search row ───────────────────────────────────────────────
        search_row = QHBoxLayout()

        self.vr_search = QLineEdit()
        self.vr_search.setPlaceholderText("🔍  Search by receipt #, cashier, or date (YYYY-MM-DD)…")
        self.vr_search.setFixedHeight(36)
        self.vr_search.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 18px;
                padding: 0 16px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #1a56db; }
        """)
        self.vr_search.returnPressed.connect(self._vr_search)

        self.vr_status_filter = QComboBox()
        self.vr_status_filter.addItems(["Completed Only", "All Statuses"])
        self.vr_status_filter.setFixedHeight(36)
        self.vr_status_filter.setFixedWidth(160)
        self.vr_status_filter.setStyleSheet("""
            QComboBox {
                background-color: #0d1117; color: #c9d1d9;
                border: 1.5px solid #30363d; border-radius: 18px;
                padding: 0 12px; font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; }
        """)

        btn_search = QPushButton("Search")
        btn_search.setFixedHeight(36)
        btn_search.setFixedWidth(90)
        btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_search.setStyleSheet("""
            QPushButton {
                background-color: #1a56db; color: #ffffff;
                border: none; border-radius: 18px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: #1e40af; }
        """)
        btn_search.clicked.connect(self._vr_search)

        btn_refresh = QPushButton("↻  Refresh")
        btn_refresh.setFixedHeight(36)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(self._vr_btn_outline)
        btn_refresh.clicked.connect(self._vr_search)

        search_row.addWidget(self.vr_search, stretch=1)
        search_row.addWidget(self.vr_status_filter)
        search_row.addWidget(btn_search)
        search_row.addWidget(btn_refresh)
        layout.addLayout(search_row)

        # ── Main splitter: transaction list | action panel ───────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #30363d; width: 1px; }")

        # ── Left: transaction list ───────────────────────────────────
        left = QFrame()
        left.setStyleSheet("background: #0d1117; border-radius: 8px;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)

        self.vr_table = QTableWidget()
        self.vr_table.setColumnCount(6)
        self.vr_table.setHorizontalHeaderLabels(["Receipt #", "Cashier", "Date", "Time", "Total", "Status"])
        self.vr_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.vr_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.vr_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.vr_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.vr_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.vr_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.vr_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.vr_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.vr_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.vr_table.verticalHeader().setVisible(False)
        self.vr_table.setShowGrid(False)
        self.vr_table.setStyleSheet("""
            QTableWidget { background: transparent; color: #c9d1d9; border: none; font-size: 12px; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #21262d; }
            QTableWidget::item:selected { background-color: #1a56db22; color: #ffffff; }
            QHeaderView::section { background: #0d1117; color: #8b949e; border: none; padding: 8px;
                                   font-size: 11px; font-weight: 700; border-bottom: 1px solid #21262d; }
        """)
        self.vr_table.selectionModel().selectionChanged.connect(self._vr_on_row_selected)
        ll.addWidget(self.vr_table)

        # ── Right: receipt detail + action panel ─────────────────────
        right = QFrame()
        right.setFixedWidth(360)
        right.setStyleSheet("background: #0d1117; border-radius: 8px;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 16, 16, 16)
        rl.setSpacing(10)

        # Receipt header
        self.vr_receipt_title = QLabel("Select a transaction")
        self.vr_receipt_title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 700;")

        self.vr_receipt_meta = QLabel("")
        self.vr_receipt_meta.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.vr_receipt_meta.setWordWrap(True)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: #30363d;")

        # Items table (with checkboxes for partial refund)
        self.vr_items_table = QTableWidget()
        self.vr_items_table.setColumnCount(5)
        self.vr_items_table.setHorizontalHeaderLabels(["✓", "Item", "Qty", "Price", "Total"])
        self.vr_items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.vr_items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.vr_items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.vr_items_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.vr_items_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.vr_items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.vr_items_table.verticalHeader().setVisible(False)
        self.vr_items_table.setShowGrid(False)
        self.vr_items_table.setStyleSheet("""
            QTableWidget { background: transparent; color: #c9d1d9; border: none; font-size: 11px; }
            QTableWidget::item { padding: 5px 4px; border-bottom: 1px solid #21262d; }
            QTableWidget::item:selected { background: transparent; }
            QHeaderView::section { background: #0d1117; color: #8b949e; border: none; padding: 5px;
                                   font-size: 10px; font-weight: 700; border-bottom: 1px solid #21262d; }
        """)

        # Totals
        self.vr_footer = QLabel("")
        self.vr_footer.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        self.vr_footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.vr_footer.setWordWrap(True)
        self.vr_footer.setTextFormat(Qt.TextFormat.RichText)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #30363d;")

        # Refund mode row
        refund_mode_row = QHBoxLayout()
        refund_mode_lbl = QLabel("Refund mode:")
        refund_mode_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        self.vr_refund_mode = QComboBox()
        self.vr_refund_mode.addItems(["Full Refund", "Partial Refund (select items)"])
        self.vr_refund_mode.setFixedHeight(30)
        self.vr_refund_mode.setStyleSheet("""
            QComboBox {
                background-color: #161b22; color: #c9d1d9;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 0 8px; font-size: 11px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background: #0d1117; color: #c9d1d9; border: 1px solid #30363d; }
        """)
        self.vr_refund_mode.currentIndexChanged.connect(self._vr_on_refund_mode_changed)
        refund_mode_row.addWidget(refund_mode_lbl)
        refund_mode_row.addWidget(self.vr_refund_mode, stretch=1)

        # Reason input
        self.vr_reason = QLineEdit()
        self.vr_reason.setPlaceholderText("Reason (required)…")
        self.vr_reason.setFixedHeight(34)
        self.vr_reason.setStyleSheet("""
            QLineEdit {
                background-color: #161b22; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 8px;
                padding: 0 12px; font-size: 12px;
            }
            QLineEdit:focus { border-color: #1a56db; }
        """)
        self.vr_reason.textChanged.connect(self._vr_update_action_buttons)

        # Selected refund amount label
        self.vr_selected_amount_lbl = QLabel("")
        self.vr_selected_amount_lbl.setStyleSheet("color: #fcd34d; font-size: 11px; font-weight: 600;")
        self.vr_selected_amount_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Action buttons
        action_row = QHBoxLayout()
        self.vr_void_btn = QPushButton("⊘  Void Transaction")
        self.vr_void_btn.setFixedHeight(38)
        self.vr_void_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vr_void_btn.setStyleSheet(self._vr_btn_red)
        self.vr_void_btn.setEnabled(False)
        self.vr_void_btn.clicked.connect(self._vr_do_void)

        self.vr_refund_btn = QPushButton("↩  Issue Refund")
        self.vr_refund_btn.setFixedHeight(38)
        self.vr_refund_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vr_refund_btn.setStyleSheet(self._vr_btn_amber)
        self.vr_refund_btn.setEnabled(False)
        self.vr_refund_btn.clicked.connect(self._vr_do_refund)

        action_row.addWidget(self.vr_void_btn, stretch=1)
        action_row.addWidget(self.vr_refund_btn, stretch=1)

        # Status banner (shown after action)
        self.vr_status_banner = QLabel("")
        self.vr_status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vr_status_banner.setStyleSheet("color: #3dd68c; font-size: 12px; font-weight: 600;")
        self.vr_status_banner.setWordWrap(True)
        self.vr_status_banner.setVisible(False)

        rl.addWidget(self.vr_receipt_title)
        rl.addWidget(self.vr_receipt_meta)
        rl.addWidget(sep1)
        rl.addWidget(self.vr_items_table, stretch=1)
        rl.addWidget(self.vr_footer)
        rl.addWidget(sep2)
        rl.addLayout(refund_mode_row)
        rl.addWidget(self.vr_reason)
        rl.addWidget(self.vr_selected_amount_lbl)
        rl.addLayout(action_row)
        rl.addWidget(self.vr_status_banner)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        layout.addWidget(splitter, stretch=1)

        # Internal state
        self._vr_selected_tx_id   = None
        self._vr_selected_tx_status = None
        self._vr_items_data        = []  # list of (item_id, name, qty, unit_price, line_total, gct)

        # Load completed transactions on open
        self._vr_load(status_filter="completed")
        return w

    # ── Void/Refund: data helpers ─────────────────────────────────────

    def _vr_load(self, query="", status_filter="completed", limit=200):
        try:
            conn = get_transactions_conn()
            sql = """
                SELECT id, cashier_name, date, time, total, status
                FROM transactions WHERE 1=1
            """
            params = []
            if query:
                sql += " AND (CAST(id AS TEXT) LIKE ? OR LOWER(cashier_name) LIKE ? OR date LIKE ?)"
                q = f"%{query.lower()}%"
                params += [q, q, q]
            if status_filter and status_filter != "all":
                sql += " AND status = ?"
                params.append(status_filter)
            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            conn.close()
        except Exception:
            rows = []

        tbl = self.vr_table
        tbl.setRowCount(len(rows))
        status_colors = {"completed": "#3dd68c", "voided": "#f87171", "refunded": "#f59e0b"}
        for row, r in enumerate(rows):
            id_item = QTableWidgetItem(f"#{r[0]}")
            id_item.setData(Qt.ItemDataRole.UserRole, r[0])
            id_item.setForeground(QColor("#ffffff"))
            cashier_item = QTableWidgetItem(r[1])
            date_item    = QTableWidgetItem(r[2])
            time_item    = QTableWidgetItem(r[3])
            total_item   = QTableWidgetItem(f"${r[4]:,.2f}")
            total_item.setForeground(QColor("#3dd68c"))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            status_text  = r[5].capitalize()
            status_item  = QTableWidgetItem(f"  {status_text}  ")
            status_item.setForeground(QColor(status_colors.get(r[5], "#8b949e")))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            for col, item in enumerate([id_item, cashier_item, date_item, time_item, total_item, status_item]):
                tbl.setItem(row, col, item)
        tbl.resizeRowsToContents()

    def _vr_search(self):
        query = self.vr_search.text().strip()
        filter_text = self.vr_status_filter.currentText()
        status = "completed" if filter_text == "Completed Only" else ""
        self._vr_load(query=query, status_filter=status)

    def _vr_on_row_selected(self):
        """Load receipt detail when a transaction row is clicked."""
        row = self.vr_table.currentRow()
        item = self.vr_table.item(row, 0)
        if not item:
            return
        tx_id = item.data(Qt.ItemDataRole.UserRole)

        try:
            conn = get_transactions_conn()
            tx = conn.execute(
                "SELECT id, cashier_name, date, time, subtotal, tax_amount, total, status "
                "FROM transactions WHERE id=?",
                (tx_id,)
            ).fetchone()
            items = conn.execute(
                "SELECT id, product_name_snapshot, quantity, unit_price_snapshot, "
                "discount_applied, line_total, gct_applicable "
                "FROM transaction_items WHERE transaction_id=?",
                (tx_id,)
            ).fetchall()
            conn.close()
        except Exception:
            return
        if not tx:
            return

        self._vr_selected_tx_id     = tx[0]
        self._vr_selected_tx_status = tx[7]
        self._vr_items_data         = list(items)  # (id, name, qty, unit_price, discount, line_total, gct)

        self.vr_receipt_title.setText(f"Receipt #{tx[0]}")
        status_color = {"completed": "#3dd68c", "voided": "#f87171", "refunded": "#f59e0b"}.get(tx[7], "#8b949e")
        self.vr_receipt_meta.setText(
            f"Cashier: {tx[1]}\n"
            f"Date: {tx[2]}  {tx[3]}\n"
            f'<span style="color:{status_color};">Status: {tx[7].capitalize()}</span>'
        )
        self.vr_receipt_meta.setTextFormat(Qt.TextFormat.RichText)

        # Populate items with checkboxes
        self.vr_items_table.setRowCount(len(items))
        for r, it in enumerate(items):
            # Checkbox cell
            chk = QCheckBox()
            chk.setChecked(True)
            chk.setStyleSheet("QCheckBox { margin-left: 6px; }")
            chk.stateChanged.connect(self._vr_update_selected_amount)
            chk_cell = QWidget()
            chk_layout = QHBoxLayout(chk_cell)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.vr_items_table.setCellWidget(r, 0, chk_cell)

            name_item  = QTableWidgetItem(it[1])
            qty_item   = QTableWidgetItem(str(it[2]))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            price_item = QTableWidgetItem(f"${it[3]:,.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            total_item = QTableWidgetItem(f"${it[5]:,.2f}")
            total_item.setForeground(QColor("#3dd68c"))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            for col, ci in enumerate([name_item, qty_item, price_item, total_item], start=1):
                self.vr_items_table.setItem(r, col, ci)

        self.vr_items_table.resizeRowsToContents()

        self.vr_footer.setText(
            f"Subtotal:  ${tx[4]:,.2f}<br>"
            f"GCT:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${tx[5]:,.2f}<br>"
            f"<b>Total:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;${tx[6]:,.2f}</b>"
        )

        # Reset UI state
        self.vr_reason.clear()
        self.vr_status_banner.setVisible(False)
        self.vr_refund_mode.setCurrentIndex(0)
        self._vr_update_selected_amount()
        self._vr_update_action_buttons()

    def _vr_on_refund_mode_changed(self, index):
        """Toggle checkbox column usability based on refund mode."""
        is_partial = (index == 1)
        for r in range(self.vr_items_table.rowCount()):
            cell = self.vr_items_table.cellWidget(r, 0)
            if cell:
                chk = cell.findChild(QCheckBox)
                if chk:
                    chk.setEnabled(is_partial)
                    chk.setChecked(True)
        self._vr_update_selected_amount()
        self._vr_update_action_buttons()

    def _vr_update_selected_amount(self):
        """Recalculate and show refund amount based on checked items."""
        if not self._vr_items_data:
            self.vr_selected_amount_lbl.setText("")
            return
        is_partial = self.vr_refund_mode.currentIndex() == 1
        if not is_partial:
            self.vr_selected_amount_lbl.setText("")
            return
        total = 0.0
        for r, it in enumerate(self._vr_items_data):
            cell = self.vr_items_table.cellWidget(r, 0)
            if cell:
                chk = cell.findChild(QCheckBox)
                if chk and chk.isChecked():
                    total += it[5]  # line_total
        self.vr_selected_amount_lbl.setText(f"Selected refund: ${total:,.2f}")

    def _vr_update_action_buttons(self):
        """Enable/disable action buttons based on selection and reason."""
        has_tx       = self._vr_selected_tx_id is not None
        is_completed = self._vr_selected_tx_status == "completed"
        has_reason   = bool(self.vr_reason.text().strip())

        self.vr_void_btn.setEnabled(has_tx and is_completed and has_reason)
        self.vr_refund_btn.setEnabled(has_tx and is_completed and has_reason)

    # ── Void / Refund: actions ────────────────────────────────────────

    def _vr_do_void(self):
        """Void the entire selected transaction."""
        if not self._vr_selected_tx_id:
            return
        reason = self.vr_reason.text().strip()
        if not reason:
            QMessageBox.warning(self, "Reason Required", "Please enter a reason before voiding.")
            return

        reply = QMessageBox.question(
            self, "Confirm Void",
            f"Void transaction Receipt #{self._vr_selected_tx_id}?\n\n"
            f"Reason: {reason}\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            conn = get_transactions_conn()
            conn.execute(
                "UPDATE transactions SET status='voided' WHERE id=?",
                (self._vr_selected_tx_id,)
            )
            # Adjust session total
            conn.execute("""
                UPDATE sessions SET total_sales = total_sales - (
                    SELECT total FROM transactions WHERE id=?
                )
                WHERE id = (SELECT session_id FROM transactions WHERE id=?)
            """, (self._vr_selected_tx_id, self._vr_selected_tx_id))
            # Adjust cashing session totals
            conn.execute("""
                UPDATE cashing_sessions
                SET total_sales = total_sales - (SELECT total FROM transactions WHERE id=?),
                    transaction_count = MAX(0, transaction_count - 1)
                WHERE status='open'
            """, (self._vr_selected_tx_id,))
            conn.commit()
            conn.close()

            self._vr_selected_tx_status = "voided"
            self.vr_receipt_meta.setText(
                self.vr_receipt_meta.text().replace("Completed", "Voided")
            )
            self.vr_void_btn.setEnabled(False)
            self.vr_refund_btn.setEnabled(False)
            self.vr_status_banner.setText(f"✓  Transaction #{self._vr_selected_tx_id} voided successfully.")
            self.vr_status_banner.setStyleSheet("color: #f87171; font-size: 12px; font-weight: 600;")
            self.vr_status_banner.setVisible(True)
            self._vr_load(status_filter="completed" if self.vr_status_filter.currentIndex() == 0 else "")
            # Print void receipt
            try:
                from printing.print_manager import print_void
                print_void(self._vr_selected_tx_id, reason, self.full_name, parent=self)
            except Exception:
                pass

        except Exception as e:
            QMessageBox.critical(self, "Void Failed", str(e))

    def _vr_do_refund(self):
        """Issue a full or partial refund for the selected transaction."""
        if not self._vr_selected_tx_id:
            return
        reason = self.vr_reason.text().strip()
        if not reason:
            QMessageBox.warning(self, "Reason Required", "Please enter a reason before refunding.")
            return

        is_partial = self.vr_refund_mode.currentIndex() == 1

        # Collect refunded items
        refund_items = []
        for r, it in enumerate(self._vr_items_data):
            include = True
            if is_partial:
                cell = self.vr_items_table.cellWidget(r, 0)
                if cell:
                    chk = cell.findChild(QCheckBox)
                    include = chk is not None and chk.isChecked()
            if include:
                refund_items.append(it)

        if not refund_items:
            QMessageBox.warning(self, "No Items", "Please select at least one item to refund.")
            return

        refund_total = sum(it[5] for it in refund_items)
        mode_label   = "Partial" if is_partial else "Full"

        reply = QMessageBox.question(
            self, f"Confirm {mode_label} Refund",
            f"{mode_label} refund for Receipt #{self._vr_selected_tx_id}\n\n"
            f"Items: {len(refund_items)}  |  Amount: ${refund_total:,.2f}\n"
            f"Reason: {reason}\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            conn = get_transactions_conn()
            if is_partial:
                # Partial refund: mark original as refunded, do NOT re-zero session total
                conn.execute(
                    "UPDATE transactions SET status='refunded' WHERE id=?",
                    (self._vr_selected_tx_id,)
                )
            else:
                # Full refund: mark voided and reverse session totals
                conn.execute(
                    "UPDATE transactions SET status='refunded' WHERE id=?",
                    (self._vr_selected_tx_id,)
                )
                conn.execute("""
                    UPDATE sessions SET total_sales = total_sales - (
                        SELECT total FROM transactions WHERE id=?
                    )
                    WHERE id = (SELECT session_id FROM transactions WHERE id=?)
                """, (self._vr_selected_tx_id, self._vr_selected_tx_id))
                conn.execute("""
                    UPDATE cashing_sessions
                    SET total_sales = total_sales - (SELECT total FROM transactions WHERE id=?),
                        transaction_count = MAX(0, transaction_count - 1)
                    WHERE status='open'
                """, (self._vr_selected_tx_id,))

            conn.commit()
            conn.close()

            self._vr_selected_tx_status = "refunded"
            self.vr_void_btn.setEnabled(False)
            self.vr_refund_btn.setEnabled(False)
            self.vr_status_banner.setText(
                f"✓  {mode_label} refund of ${refund_total:,.2f} issued for Receipt #{self._vr_selected_tx_id}."
            )
            self.vr_status_banner.setStyleSheet("color: #fcd34d; font-size: 12px; font-weight: 600;")
            self.vr_status_banner.setVisible(True)
            self._vr_load(status_filter="completed" if self.vr_status_filter.currentIndex() == 0 else "")
            # Print refund receipt
            try:
                from printing.print_manager import print_refund
                refund_dicts = [
                    {"name": it[0], "qty": it[2], "unit_price": it[3], "line_total": it[5]}
                    for it in refund_items
                ]
                print_refund(
                    self._vr_selected_tx_id, refund_dicts, refund_total,
                    reason, self.full_name, parent=self
                )
            except Exception:
                pass

        except Exception as e:
            QMessageBox.critical(self, "Refund Failed", str(e))

    # ── Products tab ─────────────────────────────────────────────────
    def _build_products_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self._build_product_list(), stretch=1)
        layout.addWidget(self._build_product_form())
        return w

    # ── Product list (left side) ─────────────────────────────────────
    def _build_product_list(self):
        panel = QFrame()
        panel.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("🔍  Search by name, barcode, brand, alias or group...")
        self.product_search.setFixedHeight(36)
        self.product_search.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 18px;
                padding: 0 16px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #1a56db; }
        """)
        self.product_search.returnPressed.connect(self._search_products)

        add_btn = QPushButton("+ Add Product")
        add_btn.setFixedHeight(36)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a56db; color: #ffffff;
                border: none; border-radius: 18px;
                font-size: 13px; font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #1145b0; }
        """)
        add_btn.clicked.connect(self._new_product_form)

        toolbar.addWidget(self.product_search, stretch=1)
        toolbar.addWidget(add_btn)

        # Product table
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(8)
        self.product_table.setHorizontalHeaderLabels(
            ["Name", "Barcode", "Brand", "Price", "Group", "GCT", "Type", "Actions"]
        )
        self.product_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, w_ in enumerate([110, 100, 90, 100, 60, 60, 80], start=1):
            self.product_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.product_table.setColumnWidth(col, w_)
        self.product_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.product_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.setShowGrid(False)
        self.product_table.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117; color: #ffffff;
                border: none; border-radius: 8px; font-size: 13px;
            }
            QHeaderView::section {
                background-color: #161b22; color: #8b949e;
                font-size: 12px; font-weight: 700;
                padding: 8px; border: none;
                border-bottom: 1px solid #30363d;
            }
            QTableWidget::item { padding: 6px 8px; border: none; }
            QTableWidget::item:selected { background-color: #21262d; }
            QScrollBar:vertical { background: #161b22; width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #30363d; border-radius: 3px; }
        """)
        self.product_table.doubleClicked.connect(self._on_table_double_click)
        self.product_table.keyPressEvent = self._on_table_key_press

        layout.addLayout(toolbar)
        layout.addWidget(self.product_table, stretch=1)

        # Load all products on start
        self._load_products()
        return panel

    # ── Product form (right side) ────────────────────────────────────
    def _build_product_form(self):
        scroll = QScrollArea()
        scroll.setFixedWidth(285)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background: #0d1117; border: none; border-radius: 8px; }
            QScrollBar:vertical { background: #0d1117; width: 5px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #30363d; border-radius: 3px; }
        """)

        form_widget = QWidget()
        form_widget.setStyleSheet("background-color: #0d1117;")
        layout = QVBoxLayout(form_widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Title
        self.form_title = QLabel("➕  Add Product")
        self.form_title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 700;")

        # ── Fields ──────────────────────────────────────────────────
        self.f_barcode  = self._form_input("Barcode",  "Scan or type barcode")
        self.f_brand    = self._form_input("Brand",    "e.g. Coca Cola")
        self.f_name     = self._form_input("Name",     "e.g. Coca Cola 330ml")
        self.f_alias    = self._form_input("Alias",    "e.g. coca-cola")
        self.f_cost     = self._form_input("Cost",     "0.00")
        self.f_cost.setValidator(QDoubleValidator(0, 999999, 2))

        # Selling price — read-only, auto-computed from cost + group profit
        self.f_selling_price = self._form_input("Selling Price", "")
        self.f_selling_price.setReadOnly(True)
        self.f_selling_price.setStyleSheet("""
            QLineEdit {
                background-color: #0d1a10; color: #3fb950;
                border: 1px solid #1a3a20; border-radius: 6px;
                padding: 0 10px; font-size: 13px;
            }
        """)
        # Selling price hint label
        self.selling_price_hint = QLabel("")
        self.selling_price_hint.setStyleSheet("color: #484f58; font-size: 10px; font-style: italic;")

        # Connect cost + group changes to selling price recalc
        self.f_cost.textChanged.connect(self._calc_selling_price)

        # Setup alias autocomplete
        self._setup_alias_completer()

        # Alias pulled price hint
        self.alias_hint = QLabel("")
        self.alias_hint.setStyleSheet("color: #4493f8; font-size: 11px;")
        self.alias_hint.setVisible(False)
        self.f_alias.textChanged.connect(self._on_alias_changed)

        # Group field with autocomplete
        grp_lbl = QLabel("Group")
        grp_lbl.setStyleSheet("color: #8b949e; font-size: 11px; text-transform: uppercase;")
        self.f_group = QComboBox()
        self.f_group.setStyleSheet(self._combo_style())
        self._populate_groups()
        self.f_group.currentIndexChanged.connect(self._calc_selling_price)

        # Discount level dropdown
        disc_lbl = QLabel("Discount Level")
        disc_lbl.setStyleSheet("color: #8b949e; font-size: 11px; text-transform: uppercase;")
        self.f_discount = QComboBox()
        self.f_discount.setStyleSheet(self._combo_style())
        self._populate_discount_levels()

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("background-color: #21262d; max-height: 1px; border: none;")

        # Toggles
        self.t_gct  = self._toggle_row("GCT Applicable")
        self.t_case = self._toggle_row("Case Item")
        self.t_gct.setChecked(True)
        self.t_case.stateChanged.connect(self._on_case_toggled)

        # ── Case fields box ──────────────────────────────────────────
        self.case_box = QFrame()
        self.case_box.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #1a3a20;
                border-radius: 6px;
            }
        """)
        self.case_box.setVisible(False)
        case_layout = QVBoxLayout(self.case_box)
        case_layout.setContentsMargins(10, 10, 10, 10)
        case_layout.setSpacing(8)

        case_title = QLabel("📦  Case Details")
        case_title.setStyleSheet("color: #3fb950; font-size: 11px; font-weight: 700; background: transparent;")

        self.f_case_qty    = self._form_input("Case Quantity", "e.g. 24")
        self.f_case_qty.setValidator(QIntValidator(1, 9999))

        self.f_case_price  = self._form_input("Auto-calculated Price", "")
        self.f_case_price.setReadOnly(True)
        self.f_case_price.setStyleSheet("""
            QLineEdit {
                background-color: #0d1a10; color: #3fb950;
                border: 1px solid #1a3a20; border-radius: 6px;
                padding: 7px 10px; font-size: 13px;
            }
        """)

        self.case_formula = QLabel("")
        self.case_formula.setStyleSheet("color: #484f58; font-size: 10px; font-style: italic; background: transparent;")

        # Connect case calc triggers
        self.f_case_qty.textChanged.connect(self._calc_case_price)
        self.f_alias.textChanged.connect(self._calc_case_price)

        case_layout.addWidget(case_title)
        case_layout.addWidget(self._field_wrap("Case Quantity",         self.f_case_qty))
        case_layout.addWidget(self._field_wrap("Auto-calculated Price", self.f_case_price))
        case_layout.addWidget(self.case_formula)

        # Save / Cancel buttons
        btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(38)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 19px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        self.cancel_btn.clicked.connect(self._clear_form)

        self.save_btn = QPushButton("Save Product")
        self.save_btn.setFixedHeight(38)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a56db; color: #ffffff;
                border: none; border-radius: 19px;
                font-size: 13px; font-weight: 700;
            }
            QPushButton:hover { background-color: #1145b0; }
        """)
        self.save_btn.clicked.connect(self._save_product)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn, stretch=1)

        # Assemble form
        layout.addWidget(self.form_title)
        layout.addWidget(self._field_wrap("Barcode",        self.f_barcode))
        layout.addWidget(self._field_wrap("Brand",          self.f_brand))
        layout.addWidget(self._field_wrap("Name",           self.f_name))
        layout.addWidget(self._field_wrap("Alias",          self.f_alias))
        layout.addWidget(self.alias_hint)
        layout.addWidget(self._field_wrap("Cost",           self.f_cost))
        layout.addWidget(self._field_wrap("Selling Price",  self.f_selling_price))
        layout.addWidget(self.selling_price_hint)
        layout.addWidget(grp_lbl)
        layout.addWidget(self.f_group)
        layout.addWidget(disc_lbl)
        layout.addWidget(self.f_discount)
        layout.addWidget(div)
        layout.addWidget(self.t_gct)
        layout.addWidget(self.t_case)
        layout.addWidget(self.case_box)
        layout.addLayout(btn_row)
        layout.addStretch()

        scroll.setWidget(form_widget)
        return scroll

    # ----------------------------------------------------------------
    # FORM HELPERS
    # ----------------------------------------------------------------

    def _form_input(self, label, placeholder):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(34)
        inp.setStyleSheet("""
            QLineEdit {
                background-color: #161b22; color: #ffffff;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 0 10px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #1a56db; }
            QLineEdit:read-only { background-color: #0d1117; color: #484f58; }
        """)
        return inp

    def _field_wrap(self, label, widget):
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8b949e; font-size: 11px; text-transform: uppercase; background: transparent;")
        layout.addWidget(lbl)
        layout.addWidget(widget)
        return wrap

    def _toggle_row(self, label):
        cb = QCheckBox(label)
        cb.setStyleSheet("""
            QCheckBox {
                color: #8b949e; font-size: 13px; spacing: 8px;
            }
            QCheckBox::indicator {
                width: 36px; height: 20px;
                border-radius: 10px; background-color: #30363d;
            }
            QCheckBox::indicator:checked { background-color: #1a56db; }
        """)
        return cb

    def _combo_style(self):
        return """
            QComboBox {
                background-color: #161b22; color: #ffffff;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 6px 10px; font-size: 13px;
            }
            QComboBox:focus { border-color: #1a56db; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #161b22; color: #ffffff;
                selection-background-color: #1a56db;
                border: 1px solid #30363d;
            }
        """

    def _badge(self, text, color, bg):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"color: {color}; background-color: {bg}; "
            f"border-radius: 4px; padding: 2px 7px; font-size: 11px;"
        )
        return lbl

    # ----------------------------------------------------------------
    # AUTOCOMPLETE SETUP
    # ----------------------------------------------------------------

    def _setup_alias_completer(self):
        """Setup alias field with autocomplete suggestions."""
        self.alias_completer = QCompleter()
        self.alias_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.alias_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.f_alias.setCompleter(self.alias_completer)
        self._update_alias_suggestions()

    def _setup_group_completer(self):
        """Setup group field with autocomplete suggestions."""
        self.group_completer = QCompleter()
        self.group_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.group_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.f_group.setCompleter(self.group_completer)
        self._update_group_suggestions()

    def _update_alias_suggestions(self):
        """Refresh alias autocomplete suggestions from database."""
        conn = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT alias_name FROM aliases ORDER BY alias_name")
        aliases = [row[0] for row in cursor.fetchall()]
        conn.close()

        model = QStringListModel(aliases)
        self.alias_completer.setModel(model)

    def _update_group_suggestions(self):
        """Refresh group autocomplete suggestions from database."""
        conn = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT group_name FROM product_groups ORDER BY group_name")
        groups = [row[0] for row in cursor.fetchall()]
        conn.close()

        model = QStringListModel(groups)
        self.group_completer.setModel(model)

    # ----------------------------------------------------------------
    # CASE TOGGLE & ALIAS LOGIC
    # ----------------------------------------------------------------

    def _on_case_toggled(self, state):
        is_case = state == Qt.CheckState.Checked.value
        self.case_box.setVisible(is_case)
        # Cost and group are disabled for cases — case cost derives from single via alias
        self.f_cost.setReadOnly(is_case)
        self.f_cost.setStyleSheet("""
            QLineEdit {
                background-color: %s; color: %s;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 0 10px; font-size: 13px;
            }
        """ % (("#0d1117", "#484f58") if is_case else ("#161b22", "#ffffff")))
        self.f_group.setEnabled(not is_case)
        if is_case:
            self.f_selling_price.clear()
            self.selling_price_hint.setText("Case price auto-calculated below")
            self._calc_case_price()
        else:
            self.selling_price_hint.setText("")
            self._calc_selling_price()

    def _on_alias_changed(self):
        alias = self.f_alias.text().strip()
        if not alias:
            self.alias_hint.setVisible(False)
            return
        is_case = self.t_case.isChecked()
        single = self._get_single_by_alias(alias)
        if single:
            pid, name, cost, selling_price, group_id, group_name = single
            if is_case:
                self.alias_hint.setText(f"↳ Single found: {name}  (cost ${cost:.2f})")
                self.alias_hint.setVisible(True)
                self._calc_case_price()
            else:
                # Auto-inherit group, cost (if blank), and discount level from alias sibling
                if group_id:
                    idx = self.f_group.findData(group_id)
                    if idx >= 0:
                        self.f_group.setCurrentIndex(idx)

                # Auto-fill discount level
                try:
                    conn_d = get_products_conn()
                    disc_row = conn_d.execute(
                        "SELECT discount_level FROM products WHERE id=?", (pid,)
                    ).fetchone()
                    conn_d.close()
                    if disc_row and disc_row[0] is not None:
                        idx = self.f_discount.findData(disc_row[0])
                        if idx >= 0:
                            self.f_discount.setCurrentIndex(idx)
                except Exception:
                    pass

                # Auto-fill cost only if the field is currently empty
                if not self.f_cost.text().strip():
                    self.f_cost.setText(str(cost))

                self.alias_hint.setText(
                    f"↳ Inherited: {name}  |  group: {group_name or '—'}  |  cost: ${cost:.2f}"
                )
                self.alias_hint.setVisible(True)
                self._calc_selling_price()
        else:
            self.alias_hint.setText("↳ No single item found for this alias")
            self.alias_hint.setVisible(True)

    def _calc_selling_price(self, *_):
        """Auto-calculate selling price for single products: cost × (1 + group_profit%)."""
        if self.t_case.isChecked():
            return
        try:
            cost = float(self.f_cost.text() or "0")
        except ValueError:
            self.f_selling_price.clear()
            self.selling_price_hint.setText("")
            return

        group_id = self.f_group.currentData()
        if not group_id:
            # No group — sell at cost
            self.f_selling_price.setText(f"${cost:.2f}")
            self.selling_price_hint.setText("= cost (no group markup)")
            return

        # Look up group profit %
        conn = get_products_conn()
        row = conn.execute(
            "SELECT profit_percent FROM product_groups WHERE id = ?", (group_id,)
        ).fetchone()
        conn.close()

        if row:
            profit_pct = row[0]
            selling = round(cost * (1 + profit_pct / 100), 2)
            self.f_selling_price.setText(f"${selling:.2f}")
            self.selling_price_hint.setText(
                f"= ${cost:.2f} × (1 + {profit_pct:.1f}%) = ${selling:.2f}"
            )
        else:
            self.f_selling_price.setText(f"${cost:.2f}")
            self.selling_price_hint.setText("= cost (group not found)")

    def _calc_case_price(self):
        """Auto-calculate case selling price: single_cost × qty × (1 + case_profit% from business)."""
        if not self.t_case.isChecked():
            return
        alias = self.f_alias.text().strip()
        single = self._get_single_by_alias(alias)
        if not single:
            return
        _, name, single_cost, _, _, _ = single
        try:
            qty = int(self.f_case_qty.text() or "0")
        except ValueError:
            return
        if qty <= 0:
            return

        # Fetch case profit % from business settings
        try:
            bconn = get_business_conn()
            brow = bconn.execute(
                "SELECT case_profit_percent FROM business_info WHERE id=1"
            ).fetchone()
            bconn.close()
            profit = brow[0] if brow else 14.0
        except Exception:
            profit = 14.0

        case_cost = round(single_cost * qty, 4)
        selling   = round(case_cost * (1 + profit / 100), 2)
        self.f_case_price.setText(f"${selling:.2f}")
        self.f_cost.setText(str(case_cost))
        self.case_formula.setText(
            f"= (${single_cost:.2f} × {qty}) × (1 + {profit:.0f}% case profit) = ${selling:.2f}"
        )

    def _get_single_by_alias(self, alias):
        """Return (id, name, cost, selling_price, group_id, group_name) of single item with this alias."""
        if not alias:
            return None
        conn   = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.cost, p.selling_price, p.group_id, pg.group_name
            FROM products p
            INNER JOIN aliases a ON a.id = p.alias_id
            LEFT JOIN product_groups pg ON pg.id = p.group_id
            WHERE a.alias_name = ? AND p.is_case = 0
            LIMIT 1
        """, (alias,))
        row = cursor.fetchone()
        conn.close()
        return row

    # ----------------------------------------------------------------
    # PRODUCT TABLE
    # ----------------------------------------------------------------

    def _load_products(self, query=""):
        conn   = get_products_conn()
        cursor = conn.cursor()
        if query:
            like = f"%{query}%"
            cursor.execute("""
                SELECT p.id, p.name, p.barcode, p.brand, p.cost, p.selling_price,
                       pg.group_name, p.gct_applicable, p.is_case
                FROM products p
                LEFT JOIN product_groups pg ON pg.id = p.group_id
                WHERE p.name LIKE ? OR p.barcode LIKE ?
                   OR p.brand LIKE ?
                   OR pg.group_name LIKE ?
                ORDER BY p.name
            """, (like, like, like, like))
        else:
            cursor.execute("""
                SELECT p.id, p.name, p.barcode, p.brand, p.cost, p.selling_price,
                       pg.group_name, p.gct_applicable, p.is_case
                FROM products p
                LEFT JOIN product_groups pg ON pg.id = p.group_id
                ORDER BY p.name
            """)
        rows = cursor.fetchall()
        conn.close()
        self._populate_table(rows)

    def _populate_table(self, rows):
        self.product_table.setRowCount(len(rows))
        center = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        left   = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

        for row, r in enumerate(rows):
            pid, name, barcode, brand, cost, selling_price, group, gct, is_case = r

            def cell(text, color="#ffffff", align=left):
                c = QTableWidgetItem(str(text or ""))
                c.setForeground(QColor(color))
                c.setTextAlignment(align)
                c.setData(Qt.ItemDataRole.UserRole, pid)
                return c

            self.product_table.setItem(row, 0, cell(name))
            self.product_table.setItem(row, 1, cell(barcode, "#4493f8"))
            self.product_table.setItem(row, 2, cell(brand or "—", "#8b949e"))
            self.product_table.setItem(row, 3, cell(f"${selling_price:.2f}", "#3fb950", center))
            self.product_table.setItem(row, 4, cell(group or "—", "#8b949e"))

            # GCT badge
            gct_lbl = self._badge(
                "GCT" if gct else "No GCT",
                "#4493f8" if gct else "#8b949e",
                "#1a2a3a" if gct else "#2a2a2a"
            )
            self.product_table.setCellWidget(row, 5, gct_lbl)

            # Type badge
            type_lbl = self._badge(
                "Case" if is_case else "Single",
                "#3fb950" if is_case else "#8b949e",
                "#1a3a2a" if is_case else "#2a2a3a"
            )
            self.product_table.setCellWidget(row, 6, type_lbl)

            # Action buttons
            actions = QWidget()
            actions.setStyleSheet("background: transparent;")
            act_layout = QHBoxLayout(actions)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(4)

            edit_btn = QPushButton("✏")
            edit_btn.setFixedSize(28, 26)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #8b949e;
                    border: 1px solid #30363d; border-radius: 4px; font-size: 12px;
                }
                QPushButton:hover { border-color: #1a56db; color: #ffffff; }
            """)
            edit_btn.clicked.connect(lambda _, i=pid: self._edit_product(i))

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(28, 26)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #8b949e;
                    border: 1px solid #30363d; border-radius: 4px; font-size: 12px;
                }
                QPushButton:hover { border-color: #f85149; color: #f85149; }
            """)
            del_btn.clicked.connect(lambda _, i=pid: self._delete_product(i))

            act_layout.addWidget(edit_btn)
            act_layout.addWidget(del_btn)
            self.product_table.setCellWidget(row, 7, actions)
            self.product_table.setRowHeight(row, 38)

    def _search_products(self):
        self._load_products(self.product_search.text().strip())

    def _on_table_double_click(self, index):
        """Double-click a product row to edit it."""
        row = index.row()
        if row >= 0 and row < self.product_table.rowCount():
            product_id = self.product_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if product_id:
                self._edit_product(product_id)

    def _on_table_key_press(self, event):
        """Handle key presses in product table."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current = self.product_table.currentRow()
            if current >= 0:
                product_id = self.product_table.item(current, 0).data(Qt.ItemDataRole.UserRole)
                if product_id:
                    self._edit_product(product_id)
        else:
            QTableWidget.keyPressEvent(self.product_table, event)

    # ----------------------------------------------------------------
    # FORM ACTIONS
    # ----------------------------------------------------------------

    def _new_product_form(self):
        """Clear the form and switch to add mode."""
        self.editing_product_id = None
        self.form_title.setText("➕  Add Product")
        self._clear_form_fields()

    def _clear_form(self):
        self.editing_product_id = None
        self.form_title.setText("➕  Add Product")
        self._clear_form_fields()

    def _clear_form_fields(self):
        self.f_barcode.clear()
        self.f_brand.clear()
        self.f_name.clear()
        self.f_alias.clear()
        self.f_cost.clear()
        self.f_selling_price.clear()
        self.selling_price_hint.setText("")
        self.f_case_qty.clear()
        self.f_case_price.clear()
        self.case_formula.setText("")
        self.alias_hint.setVisible(False)
        self.t_gct.setChecked(True)
        self.t_case.setChecked(False)
        self.case_box.setVisible(False)
        self.f_group.setCurrentIndex(0)
        self.f_discount.setCurrentIndex(0)

    def _edit_product(self, product_id):
        """Load product data into the form for editing."""
        conn   = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.barcode, p.brand, p.name, p.cost, p.selling_price,
                   a.alias_name, p.group_id, p.discount_level,
                   p.gct_applicable, p.is_case, p.case_quantity
            FROM products p
            LEFT JOIN aliases a ON a.id = p.alias_id
            WHERE p.id = ?
        """, (product_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return

        pid, barcode, brand, name, cost, selling_price, alias, group_id, disc_id, gct, is_case, case_qty = row
        self.editing_product_id = pid
        self.form_title.setText("✏  Edit Product")

        self.f_barcode.setText(barcode or "")
        self.f_brand.setText(brand   or "")
        self.f_name.setText(name     or "")
        self.f_alias.setText(alias   or "")
        self.f_cost.setText(str(cost))
        self.f_selling_price.setText(f"${selling_price:.2f}")
        self.t_gct.setChecked(bool(gct))
        self.t_case.setChecked(bool(is_case))

        if is_case and case_qty:
            self.f_case_qty.setText(str(case_qty))

        # Set group combo
        idx = self.f_group.findData(group_id)
        if idx >= 0:
            self.f_group.setCurrentIndex(idx)

        # Set discount combo
        idx = self.f_discount.findData(disc_id)
        if idx >= 0:
            self.f_discount.setCurrentIndex(idx)

    def _save_product(self):
        """Save new or edited product to the database."""
        barcode = self.f_barcode.text().strip()
        brand   = self.f_brand.text().strip()
        name    = self.f_name.text().strip()
        alias   = self.f_alias.text().strip()
        is_case = 1 if self.t_case.isChecked() else 0
        gct     = 1 if self.t_gct.isChecked()  else 0

        if not barcode or not name:
            QMessageBox.warning(self, "Missing Fields",
                                "Barcode and Name are required.")
            return

        try:
            cost = float(self.f_cost.text() or "0")
        except ValueError:
            QMessageBox.warning(self, "Invalid Cost", "Please enter a valid cost.")
            return

        case_qty = None
        if is_case:
            try:
                case_qty = int(self.f_case_qty.text() or "0")
            except ValueError:
                case_qty = 0

        # Capture original cost for sibling propagation (single products only)
        _original_cost = None
        if self.editing_product_id:
            try:
                _oc = get_products_conn()
                _or = _oc.execute(
                    "SELECT cost FROM products WHERE id=?", (self.editing_product_id,)
                ).fetchone()
                _oc.close()
                _original_cost = _or[0] if _or else None
            except Exception:
                pass

        # Cases cannot have a group — use group_id directly from combo data
        group_id_direct = None if is_case else self.f_group.currentData()
        disc_id    = self.f_discount.currentData()

        try:
            conn   = get_products_conn()
            cursor = conn.cursor()

            # Get or create alias
            alias_id = None
            if alias:
                cursor.execute(
                    "INSERT OR IGNORE INTO aliases (alias_name) VALUES (?)", (alias,))
                cursor.execute(
                    "SELECT id FROM aliases WHERE alias_name = ?", (alias,))
                alias_id = cursor.fetchone()[0]

            # Group is already resolved to an ID from the combo
            group_id = group_id_direct

            # Compute selling_price for singles
            if not is_case:
                if group_id:
                    cursor.execute(
                        "SELECT profit_percent FROM product_groups WHERE id = ?", (group_id,))
                    pct_row = cursor.fetchone()
                    profit_pct = pct_row[0] if pct_row else 0.0
                    selling_price = round(cost * (1 + profit_pct / 100), 2)
                else:
                    selling_price = cost  # no group — sell at cost
            else:
                # Case: cost derived from single; selling_price from case_profit %
                bconn = get_business_conn()
                case_pct = bconn.execute(
                    "SELECT case_profit_percent FROM business_info WHERE id=1"
                ).fetchone()
                bconn.close()
                case_pct = case_pct[0] if case_pct else 14.0
                selling_price = round(cost * (1 + case_pct / 100), 2)

            if self.editing_product_id:
                cursor.execute("""
                    UPDATE products SET
                        barcode = ?, brand = ?, name = ?, cost = ?, selling_price = ?,
                        alias_id = ?, group_id = ?, discount_level = ?,
                        gct_applicable = ?, is_case = ?, case_quantity = ?
                    WHERE id = ?
                """, (barcode, brand, name, cost, selling_price, alias_id, group_id,
                      disc_id, gct, is_case, case_qty,
                      self.editing_product_id))

                if alias_id:
                    cursor.execute(
                        "UPDATE aliases SET description = ? WHERE id = ?", (name, alias_id))
            else:
                cursor.execute("""
                    INSERT INTO products
                        (barcode, brand, name, cost, selling_price, alias_id, group_id,
                         discount_level, gct_applicable, is_case, case_quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (barcode, brand, name, cost, selling_price, alias_id, group_id,
                      disc_id, gct, is_case, case_qty))

            conn.commit()

            # Cascade: if this is a single with an alias, recalculate linked cases
            saved_id = self.editing_product_id or cursor.lastrowid
            if not is_case and alias_id:
                recalculate_selling_prices(conn=conn, product_ids=[saved_id])
            else:
                conn.commit()

            conn.close()

            # ── Ask to propagate cost change to alias siblings ───────
            if (not is_case and alias_id and _original_cost is not None
                    and abs(cost - _original_cost) > 0.001):
                try:
                    conn_s = get_products_conn()
                    siblings = conn_s.execute(
                        "SELECT id, name FROM products "
                        "WHERE alias_id=? AND is_case=0 AND id!=?",
                        (alias_id, saved_id)
                    ).fetchall()
                    conn_s.close()
                except Exception:
                    siblings = []
                if siblings:
                    names_str = "\n".join(f"  • {s[1]}" for s in siblings)
                    reply2 = QMessageBox.question(
                        self, "Update Related Products",
                        f"Cost changed from ${_original_cost:.2f} → ${cost:.2f}.\n\n"
                        f"Apply the same cost to these products sharing the same alias?\n\n"
                        f"{names_str}",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply2 == QMessageBox.StandardButton.Yes:
                        try:
                            conn_u = get_products_conn()
                            for sid, _ in siblings:
                                conn_u.execute(
                                    "UPDATE products SET cost=? WHERE id=?", (cost, sid)
                                )
                            conn_u.commit()
                            conn_u.close()
                            recalculate_selling_prices(product_ids=[s[0] for s in siblings])
                        except Exception as e:
                            QMessageBox.warning(self, "Update Error", str(e))

            QMessageBox.information(self, "Saved",
                                    f"Product '{name}' saved successfully!")
            self._clear_form()
            self._update_alias_suggestions()
            # Refresh the group combo with latest data
            self.f_group.clear()
            self._populate_groups()
            self._load_products()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save product:\n{e}")



    def _delete_product(self, product_id):
        """Delete a product after confirmation."""
        conn   = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return

        reply = QMessageBox.question(
            self, "Delete Product",
            f"Are you sure you want to delete '{row[0]}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            conn   = get_products_conn()
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
            conn.close()
            self._load_products()

    # ----------------------------------------------------------------
    # POPULATE DROPDOWNS
    # ----------------------------------------------------------------

    def _populate_groups(self):
        self.f_group.addItem("— None —", None)
        conn   = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, group_name FROM product_groups ORDER BY group_name")
        for gid, gname in cursor.fetchall():
            self.f_group.addItem(gname, gid)
        conn.close()

    def _populate_discount_levels(self):
        self.f_discount.addItem("— None —", None)
        conn   = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, level_name FROM discount_levels ORDER BY id")
        for did, dname in cursor.fetchall():
            self.f_discount.addItem(dname, did)
        conn.close()

    # ----------------------------------------------------------------
    # CLOCK
    # ----------------------------------------------------------------

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.setText(
            f"Date: {now.strftime('%B %d, %Y')}  |  Time: {now.strftime('%I:%M %p')}"
        )

    # ================================================================
    # LABELS TAB
    # ================================================================

    # ── Page/label size presets ──────────────────────────────────────
    # Format: (w_mm, h_mm, display_name, is_page_mode)
    # is_page_mode=True  → multiple labels on standard paper (A4/Letter/Legal/POS roll)
    # is_page_mode=False → single label page (thermal label printer)
    _LABEL_SIZES = [
        # ── Label/tag sizes (label printer) ──────────────────────────
        (38,  21,  "38 × 21 mm  (small price tag)", False),
        (50,  30,  "50 × 30 mm  (standard shelf)",  False),
        (70,  40,  "70 × 40 mm  (large shelf)",     False),
        (100, 50,  "100 × 50 mm  (case label)",     False),
        # ── Page layouts (normal/POS roll printer) ───────────────────
        ("A4",     None, "A4  (210 × 297 mm)",      True),
        ("Letter", None, "Letter  (216 × 279 mm)",  True),
        ("Legal",  None, "Legal  (216 × 356 mm)",   True),
        ("POS55",  None, "POS Roll  55 mm wide",    True),
        ("POS57",  None, "POS Roll  57 mm wide",    True),
        ("POS76",  None, "POS Roll  76 mm wide",    True),
    ]

    # Labels per row for each page format (depends on label size + page width)
    _PAGE_COLS = {
        "A4":     3,   # 3 × 50mm labels across 210mm with margins
        "Letter": 3,
        "Legal":  3,
        "POS55":  1,
        "POS57":  1,
        "POS76":  1,
    }

    def _build_labels_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        root = QHBoxLayout(w)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        root.addWidget(self._build_label_left(),  stretch=1)
        root.addWidget(self._build_label_right(), stretch=0)
        return w

    # ── Left: product table with checkboxes ──────────────────────────
    def _build_label_left(self):
        panel = QFrame()
        panel.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Toolbar row
        toolbar = QHBoxLayout()
        self.label_search = QLineEdit()
        self.label_search.setPlaceholderText("🔍  Search product by name, barcode or brand…")
        self.label_search.setFixedHeight(36)
        self.label_search.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 18px;
                padding: 0 16px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #1a56db; }
        """)
        self.label_search.textChanged.connect(self._label_filter_products)

        sel_all_btn = QPushButton("Select All")
        sel_all_btn.setFixedHeight(32)
        sel_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sel_all_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #8b949e;
                border: 1px solid #30363d; border-radius: 16px;
                font-size: 11px; padding: 0 12px;
            }
            QPushButton:hover { color: #ffffff; border-color: #1a56db; }
        """)
        sel_all_btn.clicked.connect(self._label_select_all)

        clr_btn = QPushButton("Clear")
        clr_btn.setFixedHeight(32)
        clr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clr_btn.setStyleSheet(sel_all_btn.styleSheet())
        clr_btn.clicked.connect(self._label_clear_selection)

        self.label_sel_count = QLabel("0 selected")
        self.label_sel_count.setStyleSheet("color: #8b949e; font-size: 11px;")

        toolbar.addWidget(self.label_search, stretch=1)
        toolbar.addWidget(sel_all_btn)
        toolbar.addWidget(clr_btn)
        toolbar.addWidget(self.label_sel_count)

        # Product table with checkboxes
        self.label_product_table = QTableWidget()
        self.label_product_table.setColumnCount(5)
        self.label_product_table.setHorizontalHeaderLabels(["☑", "Name", "Brand", "Barcode", "Price"])
        self.label_product_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.label_product_table.setColumnWidth(0, 36)
        self.label_product_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.label_product_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.label_product_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.label_product_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.label_product_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.label_product_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.label_product_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.label_product_table.verticalHeader().setVisible(False)
        self.label_product_table.setShowGrid(False)
        self.label_product_table.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117; color: #c9d1d9;
                border: none; border-radius: 8px; font-size: 12px;
            }
            QTableWidget::item { padding: 6px 8px; border-bottom: 1px solid #21262d; }
            QTableWidget::item:selected { background-color: #1a56db22; color: #ffffff; }
            QHeaderView::section {
                background: #0d1117; color: #8b949e; border: none;
                padding: 6px; font-size: 11px; font-weight: 700;
                border-bottom: 1px solid #21262d;
            }
        """)
        self.label_product_table.currentItemChanged.connect(self._label_on_row_changed)
        self.label_product_table.itemChanged.connect(self._label_on_item_changed)

        layout.addLayout(toolbar)
        layout.addWidget(self.label_product_table, stretch=1)

        self._label_products = {}   # pid -> dict
        self._label_checked = set() # pids currently checked
        self._label_load_products()
        return panel

    # ── Right: options + preview + print ─────────────────────────────
    def _build_label_right(self):
        panel = QFrame()
        panel.setFixedWidth(340)
        panel.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ── Label preview ─────────────────────────────────────────────
        preview_lbl = QLabel("LABEL PREVIEW")
        preview_lbl.setStyleSheet(
            "color: #8b949e; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        self.label_preview = _LabelPreviewWidget()
        self.label_preview.setFixedHeight(180)

        # ── Page / label size ─────────────────────────────────────────
        size_lbl = QLabel("PAGE / LABEL SIZE")
        size_lbl.setStyleSheet(
            "color: #8b949e; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        self.label_size_combo = QComboBox()
        self.label_size_combo.setFixedHeight(34)
        self.label_size_combo.setStyleSheet("""
            QComboBox {
                background-color: #0d1117; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 8px;
                padding: 0 12px; font-size: 13px;
            }
            QComboBox:focus { border-color: #1a56db; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #0d1117; color: #c9d1d9;
                border: 1px solid #30363d;
                selection-background-color: #1a56db;
            }
        """)
        for entry in self._LABEL_SIZES:
            w_val, h_val, display, is_page = entry
            self.label_size_combo.addItem(display, entry)
        self.label_size_combo.currentIndexChanged.connect(self._label_update_preview)

        # ── Show on label ─────────────────────────────────────────────
        show_lbl = QLabel("SHOW ON LABEL")
        show_lbl.setStyleSheet(
            "color: #8b949e; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        chk_style = "color: #c9d1d9; font-size: 13px;"
        self.label_chk_name    = QCheckBox("Product Name");  self.label_chk_name.setChecked(True)
        self.label_chk_brand   = QCheckBox("Brand");         self.label_chk_brand.setChecked(True)
        self.label_chk_price   = QCheckBox("Price");         self.label_chk_price.setChecked(True)
        self.label_chk_barcode = QCheckBox("Barcode");       self.label_chk_barcode.setChecked(True)
        for chk in (self.label_chk_name, self.label_chk_brand,
                    self.label_chk_price, self.label_chk_barcode):
            chk.setStyleSheet(chk_style)
            chk.stateChanged.connect(self._label_update_preview)

        # ── Copies per product ────────────────────────────────────────
        copies_row = QHBoxLayout()
        copies_lbl = QLabel("Copies per product:")
        copies_lbl.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        self.label_copies = QSpinBox()
        self.label_copies.setMinimum(1)
        self.label_copies.setMaximum(999)
        self.label_copies.setValue(1)
        self.label_copies.setFixedWidth(80)
        self.label_copies.setFixedHeight(32)
        self.label_copies.setStyleSheet("""
            QSpinBox {
                background-color: #0d1117; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 8px;
                padding: 0 10px; font-size: 13px;
            }
            QSpinBox:focus { border-color: #1a56db; }
            QSpinBox::up-button, QSpinBox::down-button {
                background: #21262d; border: none; width: 18px;
            }
        """)
        copies_row.addWidget(copies_lbl)
        copies_row.addWidget(self.label_copies)
        copies_row.addStretch()

        # ── Print button ──────────────────────────────────────────────
        self.label_print_btn = QPushButton("🖨  Print Labels")
        self.label_print_btn.setFixedHeight(42)
        self.label_print_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label_print_btn.setEnabled(False)
        self.label_print_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a56db; color: #ffffff;
                border: none; border-radius: 10px;
                font-size: 14px; font-weight: 700;
            }
            QPushButton:hover   { background-color: #1145b0; }
            QPushButton:pressed { background-color: #0e3a8a; }
            QPushButton:disabled { background-color: #1a2540; color: #4a5a7a; }
        """)
        self.label_print_btn.clicked.connect(self._label_print)

        self.label_pdf_btn = QPushButton("💾  Save as PDF")
        self.label_pdf_btn.setFixedHeight(36)
        self.label_pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.label_pdf_btn.setEnabled(False)
        self.label_pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #14532d; color: #86efac;
                border: none; border-radius: 8px;
                font-size: 12px; font-weight: 600;
            }
            QPushButton:hover   { background-color: #166534; }
            QPushButton:pressed { background-color: #15803d; }
            QPushButton:disabled { background-color: #0d2b18; color: #3a6b4a; }
        """)
        self.label_pdf_btn.clicked.connect(lambda: self._label_print(save_pdf=True))

        self.label_status = QLabel("")
        self.label_status.setStyleSheet("color: #3fb950; font-size: 12px;")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_status.setWordWrap(True)

        # ── Assemble ──────────────────────────────────────────────────
        def _div():
            f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
            f.setStyleSheet("background: #30363d; max-height: 1px; border: none;")
            return f

        layout.addWidget(preview_lbl)
        layout.addWidget(self.label_preview)
        layout.addWidget(_div())
        layout.addWidget(size_lbl)
        layout.addWidget(self.label_size_combo)
        layout.addWidget(_div())
        layout.addWidget(show_lbl)
        layout.addWidget(self.label_chk_name)
        layout.addWidget(self.label_chk_brand)
        layout.addWidget(self.label_chk_price)
        layout.addWidget(self.label_chk_barcode)
        layout.addWidget(_div())
        layout.addLayout(copies_row)
        layout.addStretch()
        layout.addWidget(self.label_print_btn)
        layout.addWidget(self.label_pdf_btn)
        layout.addWidget(self.label_status)

        return panel

    # ── Label data helpers ────────────────────────────────────────────

    def _label_load_products(self, query=""):
        conn   = get_products_conn()
        cursor = conn.cursor()
        if query:
            like = f"%{query}%"
            cursor.execute("""
                SELECT p.id, p.name, p.barcode, p.brand, p.selling_price,
                       p.alias_id, p.gct_applicable, p.discount_level
                FROM products p
                WHERE p.name LIKE ? OR p.barcode LIKE ? OR p.brand LIKE ?
                ORDER BY p.name
            """, (like, like, like))
        else:
            cursor.execute("""
                SELECT p.id, p.name, p.barcode, p.brand, p.selling_price,
                       p.alias_id, p.gct_applicable, p.discount_level
                FROM products p ORDER BY p.name
            """)
        rows = cursor.fetchall()
        conn.close()

        # Fetch GCT rate once
        try:
            from db import get_business_conn
            bconn = get_business_conn()
            gct_row = bconn.execute("SELECT tax_percent FROM business_info WHERE id=1").fetchone()
            bconn.close()
            gct_rate = gct_row[0] if gct_row else 16.5
        except Exception:
            gct_rate = 16.5

        # Fetch all discount tiers (sorted cheapest first = highest qty first)
        try:
            from db import get_products_conn as _gpc
            dconn = _gpc()
            disc_tiers = dconn.execute(
                "SELECT id, level_name, min_quantity, discount_percent "
                "FROM discount_levels ORDER BY min_quantity ASC"
            ).fetchall()
            dconn.close()
            # dict: level_id -> list of (min_qty, discount_pct)
            self._label_disc_tiers = {r[0]: (r[2], r[3]) for r in disc_tiers}
        except Exception:
            self._label_disc_tiers = {}

        tbl = self.label_product_table
        tbl.blockSignals(True)
        tbl.setRowCount(0)
        self._label_products = {}

        for pid, name, barcode, brand, price, alias_id, gct_applicable, disc_level_id in rows:
            row = tbl.rowCount()
            tbl.insertRow(row)

            # Native Qt checkable item — always visible, no widget needed
            chk_item = QTableWidgetItem()
            chk_item.setData(Qt.ItemDataRole.UserRole, pid)
            chk_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsSelectable |
                Qt.ItemFlag.ItemIsUserCheckable
            )
            chk_item.setCheckState(
                Qt.CheckState.Checked if pid in self._label_checked
                else Qt.CheckState.Unchecked
            )
            chk_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole + 1, pid)  # secondary store
            name_item.setForeground(QColor("#ffffff"))

            brand_item = QTableWidgetItem(brand or "")
            brand_item.setForeground(QColor("#8b949e"))

            bc_item = QTableWidgetItem(barcode or "")
            bc_item.setForeground(QColor("#484f58"))

            price_item = QTableWidgetItem(f"${price:.2f}")
            price_item.setForeground(QColor("#3fb950"))
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            tbl.setItem(row, 0, chk_item)
            tbl.setItem(row, 1, name_item)
            tbl.setItem(row, 2, brand_item)
            tbl.setItem(row, 3, bc_item)
            tbl.setItem(row, 4, price_item)
            tbl.setRowHeight(row, 34)

            # Build discount tiers for this product
            disc_rows = []
            if disc_level_id and disc_level_id in self._label_disc_tiers:
                min_q, pct = self._label_disc_tiers[disc_level_id]
                disc_rows.append((min_q, round(price * (1 - pct / 100), 2)))
            # Also show ALL tiers for simplicity (product level is the threshold tier)
            # Actually include all tiers that would apply at that level
            for tid, (min_q, pct) in sorted(self._label_disc_tiers.items(), key=lambda x: x[1][0]):
                discounted = round(price * (1 - pct / 100), 2)
                if (min_q, discounted) not in disc_rows:
                    disc_rows.append((min_q, discounted))

            self._label_products[pid] = {
                "name":           name,
                "barcode":        barcode or "",
                "brand":          brand or "",
                "price":          price,
                "alias_id":       alias_id,
                "gct_applicable": bool(gct_applicable),
                "gct_rate":       gct_rate,
                "disc_rows":      disc_rows,   # list of (min_qty, discounted_price)
            }

        tbl.blockSignals(False)
        self._label_refresh_count()

    def _label_on_item_changed(self, item):
        """Handle native checkbox state changes in the product table."""
        if item.column() != 0:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        if pid is None:
            return
        if item.checkState() == Qt.CheckState.Checked:
            self._label_checked.add(pid)
        else:
            self._label_checked.discard(pid)
        self._label_refresh_count()
        # Guard: buttons may not exist yet if signal fires during initial table build
        if hasattr(self, "label_print_btn"):
            self.label_print_btn.setEnabled(bool(self._label_checked))
        if hasattr(self, "label_pdf_btn"):
            self.label_pdf_btn.setEnabled(bool(self._label_checked))

    def _label_refresh_count(self):
        n = len(self._label_checked)
        self.label_sel_count.setText(f"{n} selected")

    def _label_select_all(self):
        self._label_checked = set(self._label_products.keys())
        tbl = self.label_product_table
        tbl.blockSignals(True)
        for r in range(tbl.rowCount()):
            item = tbl.item(r, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)
        tbl.blockSignals(False)
        self._label_refresh_count()
        self.label_print_btn.setEnabled(bool(self._label_checked))
        self.label_pdf_btn.setEnabled(bool(self._label_checked))

    def _label_clear_selection(self):
        self._label_checked.clear()
        tbl = self.label_product_table
        tbl.blockSignals(True)
        for r in range(tbl.rowCount()):
            item = tbl.item(r, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        tbl.blockSignals(False)
        self._label_refresh_count()
        self.label_print_btn.setEnabled(False)

    def _label_filter_products(self, text):
        self._label_load_products(text.strip())

    def _label_on_row_changed(self, current, _prev):
        """Update preview to show the currently highlighted row."""
        if not current:
            return
        row = current.row()
        chk_item = self.label_product_table.item(row, 0)
        if not chk_item:
            return
        pid  = chk_item.data(Qt.ItemDataRole.UserRole)
        data = self._label_products.get(pid)
        if data:
            self.label_preview.set_product(data)
            self._label_update_preview()

    def _label_update_preview(self):
        entry = self.label_size_combo.currentData()
        if not entry:
            return
        w_val, h_val, _, is_page = entry
        # For page layouts, preview using a representative label cell size
        if is_page:
            w_mm, h_mm = 50, 30
        else:
            w_mm, h_mm = w_val, h_val
        options = {
            "show_name":    self.label_chk_name.isChecked(),
            "show_brand":   self.label_chk_brand.isChecked(),
            "show_price":   self.label_chk_price.isChecked(),
            "show_barcode": self.label_chk_barcode.isChecked(),
            "label_w_mm":   w_mm,
            "label_h_mm":   h_mm,
        }
        self.label_preview.set_options(options)
        self.label_preview.update()

    def _label_get_siblings(self, pid):
        """Return list of sibling product dicts sharing the same alias_id (excluding pid itself)."""
        data = self._label_products.get(pid)
        if not data or not data.get("alias_id"):
            return []
        alias_id = data["alias_id"]
        siblings = []
        for other_pid, other_data in self._label_products.items():
            if other_pid != pid and other_data.get("alias_id") == alias_id:
                siblings.append((other_pid, other_data))
        return siblings

    def _label_print(self, save_pdf=False):
        if not self._label_checked:
            return

        # Collect all selected products
        selected_pids = list(self._label_checked)

        # Check if any selected product has unchecked siblings with same alias
        sibling_pids_to_ask = set()
        for pid in selected_pids:
            for sib_pid, _ in self._label_get_siblings(pid):
                if sib_pid not in self._label_checked:
                    sibling_pids_to_ask.add(sib_pid)

        if sibling_pids_to_ask:
            sibling_names = [self._label_products[p]["name"] for p in sibling_pids_to_ask]
            names_str = "\n".join(f"  • {n}" for n in sibling_names[:10])
            extra = f" (and {len(sibling_names)-10} more)" if len(sibling_names) > 10 else ""
            reply = QMessageBox.question(
                self, "Print Sibling Products?",
                f"Some selected products have related variants not selected:\n{names_str}{extra}\n\n"
                "Would you like to print labels for these variants too?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Yes:
                selected_pids += list(sibling_pids_to_ask)

        copies  = self.label_copies.value()
        options = {
            "show_name":    self.label_chk_name.isChecked(),
            "show_brand":   self.label_chk_brand.isChecked(),
            "show_price":   self.label_chk_price.isChecked(),
            "show_barcode": self.label_chk_barcode.isChecked(),
        }

        entry = self.label_size_combo.currentData()
        if not entry:
            return
        w_val, h_val, _, is_page = entry

        try:
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
            from PyQt6.QtCore import QSizeF, QMarginsF
            from PyQt6.QtGui import QPageSize, QPageLayout

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setColorMode(QPrinter.ColorMode.GrayScale)
            printer.setOrientation(QPrinter.Orientation.Portrait)

            if is_page:
                # Standard page layout with grid of labels
                page_size_map = {
                    "A4":     QPrinter.PaperSize.A4,
                    "Letter": QPrinter.PaperSize.Letter,
                    "Legal":  QPrinter.PaperSize.Legal,
                    "POS55":  None,
                    "POS57":  None,
                    "POS76":  None,
                }
                pos_widths = {"POS55": 55, "POS57": 57, "POS76": 76}

                if w_val in pos_widths:
                    roll_w = pos_widths[w_val]
                    page_size = QPageSize(
                        QSizeF(roll_w, 297),
                        QPageSize.Unit.Millimeter,
                        w_val
                    )
                    layout = QPageLayout(
                        page_size,
                        QPageLayout.Orientation.Portrait,
                        QMarginsF(2, 2, 2, 2),
                        QPageLayout.Unit.Millimeter
                    )
                    printer.setPageLayout(layout)
                    label_w_mm = roll_w - 4
                    label_h_mm = 30
                    cols = 1
                else:
                    paper = page_size_map.get(w_val, QPrinter.PaperSize.A4)
                    printer.setPaperSize(paper)
                    printer.setPageMargins(QMarginsF(8, 8, 8, 8), QPrinter.Unit.Millimeter)
                    label_w_mm = 62
                    label_h_mm = 35
                    cols = self._PAGE_COLS.get(w_val, 3)
            else:
                # Individual label size
                label_w_mm = w_val
                label_h_mm = h_val
                page_size = QPageSize(
                    QSizeF(label_w_mm, label_h_mm),
                    QPageSize.Unit.Millimeter,
                    "Label"
                )
                layout = QPageLayout(
                    page_size,
                    QPageLayout.Orientation.Portrait,
                    QMarginsF(0, 0, 0, 0),
                    QPageLayout.Unit.Millimeter
                )
                printer.setPageLayout(layout)
                cols = 1

            if save_pdf:
                from PyQt6.QtWidgets import QFileDialog
                pdf_path, _ = QFileDialog.getSaveFileName(
                    self, "Save Labels as PDF", "labels.pdf",
                    "PDF Files (*.pdf)"
                )
                if not pdf_path:
                    return
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                printer.setOutputFileName(pdf_path)
            else:
                dlg = QPrintDialog(printer, self)
                if dlg.exec() != QPrintDialog.DialogCode.Accepted:
                    return

            from PyQt6.QtGui import QPainter
            painter = QPainter()
            if not painter.begin(printer):
                self.label_status.setText("❌  Could not start printer.")
                return

            page_rect = printer.pageRect(QPrinter.Unit.DevicePixel)

            # Convert mm to device pixels
            dpi = printer.resolution()
            px_per_mm = dpi / 25.4
            lw_px = label_w_mm * px_per_mm
            lh_px = label_h_mm * px_per_mm

            # Gap between labels on page layouts
            gap_px = 3 * px_per_mm if is_page else 0

            # Build full job list: (product_data, copy_number)
            job = []
            for pid in selected_pids:
                data = self._label_products.get(pid)
                if data:
                    for _ in range(copies):
                        job.append(data)

            if is_page:
                # Grid layout — pack multiple labels per page
                x_start = page_rect.left()
                y_start = page_rect.top()
                col = 0
                row_y = y_start

                for i, data in enumerate(job):
                    x = x_start + col * (lw_px + gap_px)
                    y = row_y

                    from PyQt6.QtCore import QRectF
                    rect = QRectF(x, y, lw_px, lh_px)
                    opts = dict(options, label_w_mm=label_w_mm, label_h_mm=label_h_mm)
                    _draw_label(painter, rect, data, opts)

                    col += 1
                    if col >= cols:
                        col = 0
                        row_y += lh_px + gap_px
                        # New page if we exceed page height
                        if row_y + lh_px > page_rect.bottom():
                            printer.newPage()
                            row_y = y_start
            else:
                # One label per page
                from PyQt6.QtCore import QRectF
                for i, data in enumerate(job):
                    if i > 0:
                        printer.newPage()
                    rect = QRectF(page_rect.left(), page_rect.top(), lw_px, lh_px)
                    opts = dict(options, label_w_mm=label_w_mm, label_h_mm=label_h_mm)
                    _draw_label(painter, rect, data, opts)

            painter.end()
            total = len(job)
            if save_pdf:
                self.label_status.setText(
                    f"✅  Saved {total} label(s) to PDF."
                )
            else:
                self.label_status.setText(
                    f"✅  Printed {total} label(s) for {len(selected_pids)} product(s)."
                )

        except Exception as e:
            self.label_status.setText(f"❌  {e}")

    # ----------------------------------------------------------------
    # LOGOUT
    # ----------------------------------------------------------------

    def _handle_logout(self):
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            from ui.login_window import LoginWindow
            self.login = LoginWindow()
            self.login.show()
            self.force_close()

    # ----------------------------------------------------------------
    # HELPERS
    # ----------------------------------------------------------------

    def _center_on_screen(self):
        screen = self.screen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2
        )


# ──────────────────────────────────────────────────────────────────────────────
# LABEL PREVIEW WIDGET  — draws a miniature label preview in the UI
# ──────────────────────────────────────────────────────────────────────────────

class _LabelPreviewWidget(QWidget):
    """Draws a live preview of what the printed label will look like."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._product = None
        self._options = {
            "show_name": True, "show_brand": True,
            "show_price": True, "show_barcode": True,
            "label_w_mm": 50, "label_h_mm": 30,
        }
        self.setStyleSheet("background: transparent;")

    def set_product(self, data):
        self._product = data
        self.update()

    def set_options(self, options):
        self._options = options
        self.update()

    def paintEvent(self, event):
        if not self._product:
            painter = QPainter(self)
            painter.setPen(QColor("#30363d"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "Select a product to preview")
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Label aspect ratio from size options
        w_mm = self._options.get("label_w_mm", 50)
        h_mm = self._options.get("label_h_mm", 30)
        aspect = w_mm / h_mm

        # Fit label into widget keeping aspect ratio, with margin
        margin = 12
        avail_w = self.width() - margin * 2
        avail_h = self.height() - margin * 2

        if avail_w / aspect <= avail_h:
            lw = avail_w
            lh = avail_w / aspect
        else:
            lh = avail_h
            lw = avail_h * aspect

        lx = (self.width()  - lw) / 2
        ly = (self.height() - lh) / 2

        rect = QRectF(lx, ly, lw, lh)

        # Draw label background + border
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor("#1a56db"), 1.5))
        painter.drawRoundedRect(rect, 6, 6)

        # Draw content inside label
        _draw_label(painter, rect, self._product, self._options, preview=True)


# ──────────────────────────────────────────────────────────────────────────────
# SHARED LABEL DRAWING FUNCTION
# ──────────────────────────────────────────────────────────────────────────────

def _draw_label(painter, rect, product, options, preview=False):
    """
    Draw price-tag label content into `rect` using `painter`.
    Layout (top → bottom):
      Brand (small italic)
      Name (bold)
      Main price + "(inc. GCT)" tag if applicable
      Discount tier rows (smaller, each "buy N+ → $X.XX")
      Barcode strip (compact, ~20% of height)
    """
    show_name    = options.get("show_name", True)
    show_brand   = options.get("show_brand", True)
    show_price   = options.get("show_price", True)
    show_barcode = options.get("show_barcode", True)

    name    = product.get("name", "")
    brand   = product.get("brand", "")
    price   = product.get("price", 0.0)
    barcode = product.get("barcode", "")
    gct_ok  = product.get("gct_applicable", False)
    gct_rate= product.get("gct_rate", 16.5)
    disc_rows = product.get("disc_rows", [])   # list of (min_qty, discounted_price)

    x   = rect.x()
    y   = rect.y()
    w   = rect.width()
    h   = rect.height()
    pad = max(w * 0.04, 2.0)

    painter.save()
    painter.setClipRect(rect)

    # ── Reserve vertical space ────────────────────────────────────────
    # Barcode takes 22% (compact strip), discount rows take ~14% each (max 2 shown)
    shown_disc = disc_rows[:2]                          # show at most 2 tiers
    barcode_h  = h * 0.22 if show_barcode else 0
    disc_h     = (h * 0.13 * len(shown_disc)) if (show_price and shown_disc) else 0
    text_h     = h - barcode_h - disc_h

    text_sections = sum([show_brand and bool(brand), show_name, show_price])
    row_h = text_h / max(text_sections, 1)

    cur_y = y + pad * 0.5

    # ── Brand ─────────────────────────────────────────────────────────
    if show_brand and brand:
        fsize = max(int(row_h * 0.25), 5)
        font = QFont("Arial", fsize)
        font.setItalic(True)
        painter.setFont(font)
        painter.setPen(QColor("#555555") if preview else QColor("#555555"))
        tr = QRectF(x + pad, cur_y, w - pad * 2, row_h * 0.45)
        painter.drawText(tr, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         brand.upper())
        cur_y += row_h * 0.45

    # ── Name ──────────────────────────────────────────────────────────
    if show_name and name:
        fsize = max(int(row_h * 0.32), 6)
        font = QFont("Arial", fsize)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#000000"))
        tr = QRectF(x + pad, cur_y, w - pad * 2, row_h * 0.55)
        fm = QFontMetrics(font)
        elided = fm.elidedText(name, Qt.TextElideMode.ElideRight, int(w - pad * 2))
        painter.drawText(tr, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)
        cur_y += row_h * 0.58

    # ── Main price + GCT tag ──────────────────────────────────────────
    if show_price:
        price_h = row_h * 0.72

        # Big price on the right
        fsize = max(int(price_h * 0.72), 7)
        font = QFont("Arial", fsize)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#1a56db") if preview else QColor("#000080"))
        price_str = f"${price:.2f}"
        fm = QFontMetrics(font)
        price_w = fm.horizontalAdvance(price_str)
        painter.drawText(
            QRectF(x + w - pad - price_w - 2, cur_y, price_w + 4, price_h),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            price_str
        )

        # GCT tag (small, to the left of the price)
        if gct_ok:
            tag_fsize = max(int(price_h * 0.28), 5)
            tag_font = QFont("Arial", tag_fsize)
            painter.setFont(tag_font)
            painter.setPen(QColor("#b45309") if preview else QColor("#92400e"))
            tag_str = f"incl. GCT {gct_rate:.0f}%"
            tag_rect = QRectF(x + pad, cur_y + price_h * 0.55, w - pad * 2 - price_w - 6, price_h * 0.42)
            painter.drawText(tag_rect,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             tag_str)

        cur_y += price_h

        # ── Discount tier rows ─────────────────────────────────────────
        for (min_qty, disc_price) in shown_disc:
            tier_h = h * 0.13
            fsize = max(int(tier_h * 0.58), 5)
            font = QFont("Arial", fsize)
            painter.setFont(font)
            painter.setPen(QColor("#15803d") if preview else QColor("#166534"))
            tier_str = f"buy {min_qty}+  →  ${disc_price:.2f}"
            tr = QRectF(x + pad, cur_y, w - pad * 2, tier_h)
            painter.drawText(tr, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             tier_str)
            cur_y += tier_h

    # ── Barcode strip (compact) ───────────────────────────────────────
    if show_barcode and barcode and barcode_h > 4:
        bc_rect = QRectF(x + pad, cur_y + 1, w - pad * 2, barcode_h - 2)
        _draw_barcode_bars(painter, bc_rect, barcode, preview)

    painter.restore()


def _draw_barcode_bars(painter, rect, barcode_text, preview=False):
    """
    Draw Code 128 barcode bars directly with QPainter.
    Falls back to drawing the barcode number as text if encoding fails.
    Uses python-barcode if available for accurate bar widths,
    otherwise uses a simple deterministic bar pattern from the digits.
    """
    painter.save()

    try:
        import barcode as pybarcode
        from barcode.writer import BaseWriter
        import io

        # Encode barcode to get bar widths (use SVG-style data via BaseWriter trick)
        # We use the module output to extract bar pattern
        bc_class = pybarcode.get_barcode_class("code128")

        class _BarCollector(BaseWriter):
            def __init__(self):
                super().__init__()
                self.bars = []  # list of (x_frac, w_frac, is_bar)

            def render(self, code):
                # code is list of (x, y, w, h, text) or similar
                pass

            def write(self, content, fp=None, text=None):
                pass

        # Use SVG output and parse bar positions
        import io
        buf = io.BytesIO()
        bc  = bc_class(barcode_text, writer=pybarcode.writer.SVGWriter())
        bc.write(buf)
        svg_data = buf.getvalue().decode("utf-8", errors="ignore")

        # Parse <rect> elements from SVG for bar positions
        import re
        rects = re.findall(
            r'<rect[^>]+x="([^"]+)"[^>]+width="([^"]+)"[^>]+height="([^"]+)"',
            svg_data
        )
        if rects:
            # Convert to floats and normalize
            parsed = [(float(rx), float(rw)) for rx, rw, rh in rects
                      if float(rh) > 5]  # skip text underlines
            if parsed:
                min_x  = min(rx for rx, rw in parsed)
                max_x  = max(rx + rw for rx, rw in parsed)
                span   = max_x - min_x or 1

                bar_area_h = rect.height() * 0.78
                num_y      = rect.y() + bar_area_h + rect.height() * 0.04

                painter.setBrush(QBrush(QColor("#000000")))
                painter.setPen(Qt.PenStyle.NoPen)

                for rx, rw in parsed:
                    bx = rect.x() + ((rx - min_x) / span) * rect.width()
                    bw = max((rw / span) * rect.width(), 1.0)
                    painter.drawRect(QRectF(bx, rect.y(), bw, bar_area_h))

                # Draw barcode number below bars
                font = QFont("Courier New", max(int(rect.height() * 0.14), 5))
                painter.setFont(font)
                painter.setPen(QColor("#000000"))
                num_rect = QRectF(rect.x(), num_y, rect.width(), rect.height() * 0.2)
                painter.drawText(num_rect,
                                 Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                                 barcode_text)
                painter.restore()
                return

    except Exception:
        pass

    # ── Fallback: simple visual bar pattern derived from barcode digits ──
    digits = [c for c in barcode_text if c.isdigit()]
    if not digits:
        digits = [str(ord(c) % 10) for c in barcode_text[:12]]

    bar_area_h = rect.height() * 0.75
    num_y      = rect.y() + bar_area_h + rect.height() * 0.04

    # Build bar pattern: alternate narrow/wide bars based on digit values
    bars = []
    for d in digits:
        v = int(d)
        bars.append(1)           # always a narrow bar
        bars.append(v % 3 + 1)  # gap: 1-3 units wide
    # Add start/stop markers
    bars = [2, 1, 2] + bars + [2, 1, 2, 1]

    total_units = sum(bars)
    unit_w = rect.width() / max(total_units, 1)

    is_bar = True
    cur_x  = rect.x()
    painter.setPen(Qt.PenStyle.NoPen)

    for units in bars:
        bar_w = units * unit_w
        if is_bar:
            painter.setBrush(QBrush(QColor("#000000")))
            painter.drawRect(QRectF(cur_x, rect.y(), max(bar_w - 0.5, 0.5), bar_area_h))
        cur_x  += bar_w
        is_bar  = not is_bar

    # Barcode number below
    font = QFont("Courier New", max(int(rect.height() * 0.15), 5))
    painter.setFont(font)
    painter.setPen(QColor("#000000"))
    num_rect = QRectF(rect.x(), num_y, rect.width(), rect.height() * 0.22)
    painter.drawText(num_rect,
                     Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                     barcode_text)

    painter.restore()
