"""
ui/supervisor_dashboard.py
Supervisor dashboard with tabbed interface.
Tabs: Checkout | Products | Reports | Transactions | Void / Refund
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QCheckBox, QAbstractItemView,
    QMessageBox, QScrollArea, QSizePolicy, QFormLayout, QCompleter,
    QSplitter, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QStringListModel
from PyQt6.QtGui import QColor, QDoubleValidator, QIntValidator
from ui.base_window import BaseWindow
from db import get_products_conn, get_users_conn, get_transactions_conn, get_business_conn


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

        self.tabs.addTab(self._build_checkout_tab(),      "Checkout")
        self.tabs.addTab(self._build_products_tab(),      "Products")
        self.tabs.addTab(self._build_reports_tab(),       "Reports")
        self.tabs.addTab(self._build_transactions_tab(),  "Transactions")
        self.tabs.addTab(self._build_void_tab(),          "Void / Refund")
        self.tabs.setCurrentIndex(1)
        return self.tabs

    # ── Checkout tab — stub ──────────────────────────────────────────
    def _build_checkout_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        l = QVBoxLayout(w)
        lbl = QLabel("Checkout — coming soon")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #8b949e; font-size: 16px;")
        l.addWidget(lbl)
        return w

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
        self.rpt_open_btn.clicked.connect(self._rpt_open_session)

        self.rpt_print_btn = QPushButton("Print Summary")
        self.rpt_print_btn.setFixedHeight(34)
        self.rpt_print_btn.setStyleSheet(_btn_outline)
        self.rpt_print_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rpt_print_btn.setEnabled(False)

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
        self._rpt_selected_cashier_id = None
        self._rpt_selected_session_id = None

        self._rpt_load_cashiers()
        return w

    # ── Reports: data loaders ────────────────────────────────────────

    def _rpt_load_cashiers(self):
        """Load distinct cashiers from cashing_sessions + running totals."""
        try:
            conn = get_transactions_conn()
            rows = conn.execute("""
                SELECT opened_by_id, opened_by_name,
                       SUM(total_sales) AS total_sales,
                       MAX(CASE WHEN status='open' THEN 1 ELSE 0 END) AS has_open
                FROM cashing_sessions
                GROUP BY opened_by_id, opened_by_name
                ORDER BY opened_by_name
            """).fetchall()
            conn.close()
        except Exception:
            rows = []

        self._rpt_all_cashiers = [
            {"cashier_id": r[0], "cashier_name": r[1],
             "total_sales": r[2] or 0.0, "has_open": r[3]}
            for r in rows
        ]
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
        self._rpt_selected_session_id = None
        self.rpt_session_header.setText(f"Sessions  —  {cashier_name}")
        self._rpt_load_sessions(cashier_id)
        self._rpt_update_cards()

    def _rpt_load_sessions(self, cashier_id):
        try:
            conn = get_transactions_conn()
            rows = conn.execute("""
                SELECT id, status, opened_at, closed_at, total_sales,
                       total_gct, total_discount, transaction_count
                FROM cashing_sessions
                WHERE opened_by_id = ?
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

    def _rpt_open_session(self):
        reply = QMessageBox.question(
            self, "Open New Session",
            "Open a new cashing session now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            conn = get_transactions_conn()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("""
                INSERT INTO cashing_sessions
                    (opened_by_id, opened_by_name, opened_at, status)
                VALUES (?, ?, ?, 'open')
            """, (self.user_id, self.full_name, now))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Session Opened", "New cashing session opened.")
            self._rpt_load_cashiers()
            if self._rpt_selected_cashier_id is not None:
                self._rpt_load_sessions(self._rpt_selected_cashier_id)
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
        """Reprint the selected receipt. Wired to printer when receipt printing is implemented."""
        row = self.tx_table.currentRow()
        item = self.tx_table.item(row, 0)
        if not item:
            return
        tx_id = item.data(Qt.ItemDataRole.UserRole)
        QMessageBox.information(
            self, "Reprint Receipt",
            f"Reprint for Receipt #{tx_id} will be sent to the printer.\n"
            "(Receipt printing not yet implemented — wire to printer module here.)"
        )

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
        self.f_price    = self._form_input("Price",    "0.00")
        self.f_price.setValidator(QDoubleValidator(0, 999999, 2))

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
        self.f_group.setEditable(True)
        self.f_group.setStyleSheet(self._combo_style())
        self._setup_group_completer()

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
        self.f_case_profit = self._form_input("Case Profit %", "e.g. 14")
        self.f_case_profit.setValidator(QDoubleValidator(0, 100, 2))

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
        self.f_case_profit.textChanged.connect(self._calc_case_price)
        self.f_alias.textChanged.connect(self._calc_case_price)

        case_layout.addWidget(case_title)
        case_layout.addWidget(self._field_wrap("Case Quantity",         self.f_case_qty))
        case_layout.addWidget(self._field_wrap("Case Profit %",         self.f_case_profit))
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
        layout.addWidget(self._field_wrap("Price (single)", self.f_price))
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
        # Price field disabled for cases — auto-calculated
        self.f_price.setReadOnly(is_case)
        self.f_price.setStyleSheet("""
            QLineEdit {
                background-color: %s; color: %s;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 0 10px; font-size: 13px;
            }
        """ % (("#0d1117", "#484f58") if is_case else ("#161b22", "#ffffff")))
        if is_case:
            self._calc_case_price()

    def _on_alias_changed(self):
        alias = self.f_alias.text().strip()
        if not alias:
            self.alias_hint.setVisible(False)
            return
        # Look up single item price by alias
        single = self._get_single_price_by_alias(alias)
        if single:
            pid, name, price = single
            self.alias_hint.setText(f"↳ Single price pulled: ${price:.2f} ({name})")
            self.alias_hint.setVisible(True)
            self._calc_case_price()
        else:
            self.alias_hint.setText("↳ No single item found for this alias")
            self.alias_hint.setVisible(True)

    def _calc_case_price(self):
        """Auto-calculate case price from single price × qty + profit %."""
        if not self.t_case.isChecked():
            return
        alias  = self.f_alias.text().strip()
        single = self._get_single_price_by_alias(alias)
        if not single:
            return
        _, name, single_price = single
        try:
            qty    = int(self.f_case_qty.text()    or "0")
            profit = float(self.f_case_profit.text() or "0")
        except ValueError:
            return
        if qty <= 0:
            return
        base  = single_price * qty
        price = round(base * (1 + profit / 100), 2)
        self.f_case_price.setText(f"${price:.2f}")
        self.f_price.setText(str(price))
        self.case_formula.setText(
            f"= (${single_price:.2f} × {qty}) + {profit:.0f}% profit"
        )

    def _get_single_price_by_alias(self, alias):
        """Return (id, name, price) of the single item with this alias."""
        if not alias:
            return None
        conn   = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.price
            FROM products p
            INNER JOIN aliases a ON a.id = p.alias_id
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
                SELECT p.id, p.name, p.barcode, p.brand, p.price,
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
                SELECT p.id, p.name, p.barcode, p.brand, p.price,
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
            pid, name, barcode, brand, price, group, gct, is_case = r

            def cell(text, color="#ffffff", align=left):
                c = QTableWidgetItem(str(text or ""))
                c.setForeground(QColor(color))
                c.setTextAlignment(align)
                c.setData(Qt.ItemDataRole.UserRole, pid)
                return c

            self.product_table.setItem(row, 0, cell(name))
            self.product_table.setItem(row, 1, cell(barcode, "#4493f8"))
            self.product_table.setItem(row, 2, cell(brand or "—", "#8b949e"))
            self.product_table.setItem(row, 3, cell(f"${price:.2f}", "#4493f8", center))
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
        self.f_price.clear()
        self.f_case_qty.clear()
        self.f_case_profit.clear()
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
            SELECT p.id, p.barcode, p.brand, p.name, p.price,
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

        pid, barcode, brand, name, price, alias, group_id, disc_id, gct, is_case, case_qty = row
        self.editing_product_id = pid
        self.form_title.setText("✏  Edit Product")

        self.f_barcode.setText(barcode or "")
        self.f_brand.setText(brand   or "")
        self.f_name.setText(name     or "")
        self.f_alias.setText(alias   or "")
        self.f_price.setText(str(price))
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
            price = float(self.f_price.text() or "0")
        except ValueError:
            QMessageBox.warning(self, "Invalid Price", "Please enter a valid price.")
            return

        case_qty = None
        if is_case:
            try:
                case_qty = int(self.f_case_qty.text() or "0")
            except ValueError:
                case_qty = 0

        group_name = self.f_group.currentText().strip()
        disc_id  = self.f_discount.currentData()

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

            # Get or create group
            group_id = None
            if group_name and group_name != "— None —":
                cursor.execute(
                    "INSERT OR IGNORE INTO product_groups (group_name) VALUES (?)", (group_name,))
                cursor.execute(
                    "SELECT id FROM product_groups WHERE group_name = ?", (group_name,))
                group_id = cursor.fetchone()[0]

            if self.editing_product_id:
                cursor.execute("""
                    UPDATE products SET
                        barcode = ?, brand = ?, name = ?, price = ?,
                        alias_id = ?, group_id = ?, discount_level = ?,
                        gct_applicable = ?, is_case = ?, case_quantity = ?
                    WHERE id = ?
                """, (barcode, brand, name, price, alias_id, group_id,
                      disc_id, gct, is_case, case_qty,
                      self.editing_product_id))

                # Update alias description for all linked products
                if alias_id:
                    cursor.execute("""
                        UPDATE aliases SET description = ?
                        WHERE id = ?
                    """, (name, alias_id))
            else:
                cursor.execute("""
                    INSERT INTO products
                        (barcode, brand, name, price, alias_id, group_id,
                         discount_level, gct_applicable, is_case, case_quantity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (barcode, brand, name, price, alias_id, group_id,
                      disc_id, gct, is_case, case_qty))

            conn.commit()

            # POINT 2 — If editing a single item price, offer to sync alias siblings
            if self.editing_product_id and not is_case and alias_id:
                cursor.execute(
                    "SELECT id, name FROM products WHERE alias_id = ? AND is_case = 0 AND id != ?",
                    (alias_id, self.editing_product_id)
                )
                siblings = cursor.fetchall()
                conn.close()
                if siblings:
                    sibling_names = ", ".join(s[1] for s in siblings)
                    reply = QMessageBox.question(
                        self, "Sync Alias Prices",
                        f"Update price to ${price:.2f} for all other single items "
                        f"with alias '{alias}'?\n\nAffected: {sibling_names}",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        conn2 = get_products_conn()
                        for sid, _ in siblings:
                            conn2.execute("UPDATE products SET price = ? WHERE id = ?", (price, sid))
                        conn2.commit()
                        conn2.close()
            else:
                conn.close()

            QMessageBox.information(self, "Saved",
                                    f"Product '{name}' saved successfully!")
            self._clear_form()
            self._update_alias_suggestions()
            self._update_group_suggestions()
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
