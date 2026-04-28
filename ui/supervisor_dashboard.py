"""
ui/supervisor_dashboard.py
Supervisor dashboard with tabbed interface.
Tabs: Checkout | Products | Reports | Void / Refund
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QCheckBox, QAbstractItemView,
    QMessageBox, QScrollArea, QSizePolicy, QFormLayout, QCompleter
)
from PyQt6.QtCore import Qt, QTimer, QStringListModel
from PyQt6.QtGui import QColor, QDoubleValidator, QIntValidator
from ui.base_window import BaseWindow
from db import get_connection


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

        self.tabs.addTab(self._build_checkout_tab(),   "Checkout")
        self.tabs.addTab(self._build_products_tab(),   "Products")
        self.tabs.addTab(self._build_reports_tab(),    "Reports")
        self.tabs.addTab(self._build_void_tab(),       "Void / Refund")
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
    def _build_reports_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        l = QVBoxLayout(w)
        lbl = QLabel("Reports — coming soon")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #8b949e; font-size: 16px;")
        l.addWidget(lbl)
        return w

    # ── Void / Refund tab — stub ─────────────────────────────────────
    def _build_void_tab(self):
        w = QWidget()
        w.setStyleSheet("background-color: #161b22;")
        l = QVBoxLayout(w)
        lbl = QLabel("Void / Refund — coming soon")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #8b949e; font-size: 16px;")
        l.addWidget(lbl)
        return w

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
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT alias_name FROM aliases ORDER BY alias_name")
        aliases = [row[0] for row in cursor.fetchall()]
        conn.close()

        model = QStringListModel(aliases)
        self.alias_completer.setModel(model)

    def _update_group_suggestions(self):
        """Refresh group autocomplete suggestions from database."""
        conn = get_connection()
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
        conn   = get_connection()
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
        conn   = get_connection()
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
        # Unlock barcode when switching back to add mode
        self.f_barcode.setReadOnly(False)
        self.f_barcode.setStyleSheet("""
            QLineEdit {
                background-color: #161b22; color: #ffffff;
                border: 1px solid #30363d; border-radius: 6px;
                padding: 0 10px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #1a56db; }
        """)
        self.f_barcode.setToolTip("")
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
        conn   = get_connection()
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
        # Lock barcode — cannot be changed while editing
        self.f_barcode.setReadOnly(True)
        self.f_barcode.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117; color: #484f58;
                border: 1px solid #21262d; border-radius: 6px;
                padding: 0 10px; font-size: 13px;
            }
        """)
        self.f_barcode.setToolTip("Barcode cannot be changed after a product is created")
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
            conn   = get_connection()
            cursor = conn.cursor()

            # FIX 1 — Check for duplicate barcode on new products only
            if not self.editing_product_id:
                cursor.execute(
                    "SELECT id, name FROM products WHERE barcode = ?", (barcode,))
                existing = cursor.fetchone()
                if existing:
                    conn.close()
                    QMessageBox.warning(
                        self, "Duplicate Barcode",
                        f"Barcode '{barcode}' is already used by:\n'{existing[1]}'\n\n"
                        f"Please use a different barcode."
                    )
                    self.f_barcode.selectAll()
                    self.f_barcode.setFocus()
                    return

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
                # FIX 2 — Barcode NOT updated — it is locked/read-only in edit mode
                cursor.execute("""
                    UPDATE products SET
                        brand = ?, name = ?, price = ?,
                        alias_id = ?, group_id = ?, discount_level = ?,
                        gct_applicable = ?, is_case = ?, case_quantity = ?
                    WHERE id = ?
                """, (brand, name, price, alias_id, group_id,
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
        conn   = get_connection()
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
            conn   = get_connection()
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
            conn.close()
            self._load_products()

    # ----------------------------------------------------------------
    # POPULATE DROPDOWNS
    # ----------------------------------------------------------------

    def _populate_groups(self):
        self.f_group.addItem("— None —", None)
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, group_name FROM product_groups ORDER BY group_name")
        for gid, gname in cursor.fetchall():
            self.f_group.addItem(gname, gid)
        conn.close()

    def _populate_discount_levels(self):
        self.f_discount.addItem("— None —", None)
        conn   = get_connection()
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
