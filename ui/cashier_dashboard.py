"""
ui/cashier_dashboard.py
Cashier dashboard — main POS checkout screen.
Features: 3 switchable carts, F1-F8 quick keys, barcode/search,
GCT per item, totals panel, matching user's draft design.
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame,
    QListWidget, QListWidgetItem, QAbstractItemView, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from ui.base_window import BaseWindow
from db import get_products_conn, get_business_conn


# Cart colors for visual distinction
CART_COLORS = [
    "#1a56db",  # Blue
    "#1a9e6c",  # Green
    "#c7622a",  # Orange
]


class CashierDashboard(BaseWindow):
    """
    Main POS checkout screen for cashiers.
    Supports 3 independent carts with left/right navigation.
    """

    MAX_CARTS = 3

    def __init__(self, user_id, full_name):
        super().__init__()
        self.user_id    = user_id
        self.full_name  = full_name
        self.gct_rate   = self._load_gct_rate()
        self.quick_keys = self._load_quick_keys()

        # 3 independent carts
        self.carts       = [[] for _ in range(self.MAX_CARTS)]
        self.active_cart = 0

        self.setWindowTitle("POS System — Cashier")
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
        body = QHBoxLayout()
        body.setSpacing(8)
        body.addWidget(self._build_left_panel())
        body.addWidget(self._build_center_panel(), stretch=1)
        body.addWidget(self._build_right_panel())
        layout.addLayout(body, stretch=1)

    # ── Top bar ──────────────────────────────────────────────────────
    def _build_topbar(self):
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet("background-color: #1a56db; border-radius: 10px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        left = QLabel(f"POS System  |  Cashier:  {self.full_name}")
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

    # ── Left panel — F1-F8 ───────────────────────────────────────────
    def _build_left_panel(self):
        panel = QFrame()
        panel.setFixedWidth(120)
        panel.setStyleSheet("background-color: #161b22; border-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(6)

        self.fkey_buttons = []
        for i in range(8):
            btn = QPushButton()
            btn.setFixedHeight(66)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if i < len(self.quick_keys):
                qk = self.quick_keys[i]
                btn.setText(f"F{i+1}\n{qk['name']}\n${qk['price']:.2f}")
                btn.setStyleSheet(self._fkey_style())
                btn.clicked.connect(lambda _, idx=i: self._add_quick_key(idx))
            else:
                btn.setText(f"F{i+1}\n—")
                btn.setEnabled(False)
                btn.setStyleSheet(self._fkey_style(disabled=True))
            self.fkey_buttons.append(btn)
            layout.addWidget(btn)
        layout.addStretch()
        return panel

    # ── Center panel ─────────────────────────────────────────────────
    def _build_center_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background-color: #161b22; border-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header row with qty spinbox and search
        header = QHBoxLayout()
        header.setSpacing(8)

        # Quantity spinbox
        qty_lbl = QLabel("Qty:")
        qty_lbl.setStyleSheet("color: #8b949e; font-size: 12px;")
        self.qty_spinbox = QSpinBox()
        self.qty_spinbox.setMinimum(1)
        self.qty_spinbox.setMaximum(9999)
        self.qty_spinbox.setValue(1)
        self.qty_spinbox.setFixedWidth(60)
        self.qty_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #0d1117; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 6px;
                padding: 0 6px; font-size: 13px;
            }
            QSpinBox:focus { border-color: #1a56db; }
        """)

        self.search_input = QLineEdit()
        self.search_input.setFixedHeight(36)
        self.search_input.setPlaceholderText("↵ Barcode  |  Search  ↵  Checkout")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 18px;
                padding: 0 16px; font-size: 13px;
            }
            QLineEdit:focus { border-color: #1a56db; }
        """)
        self.search_input.returnPressed.connect(self._handle_search_enter)
        self.search_input.keyPressEvent = self._search_key_press

        checkout_btn = QPushButton("Checkout")
        checkout_btn.setFixedSize(110, 36)
        checkout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        checkout_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 18px;
                font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: #1a56db; border-color: #1a56db; }
        """)
        checkout_btn.clicked.connect(self._handle_checkout)

        header.addWidget(qty_lbl)
        header.addWidget(self.qty_spinbox)
        header.addWidget(self.search_input, stretch=1)
        header.addWidget(checkout_btn)

        # Search results overlay
        self.results_list = QListWidget()
        self.results_list.setVisible(False)
        self.results_list.setFixedHeight(150)
        self.results_list.setStyleSheet("""
            QListWidget {
                background-color: #21262d; color: #ffffff;
                border: 1.5px solid #1a56db; border-radius: 8px;
                font-size: 13px;
            }
            QListWidget::item { padding: 8px 14px; border-bottom: 1px solid #30363d; }
            QListWidget::item:selected { background-color: #1a56db; }
            QListWidget::item:hover    { background-color: #30363d; }
        """)
        self.results_list.itemClicked.connect(self._add_from_results)
        self.results_list.keyPressEvent = self._results_key_press

        # Cart table
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels(
            ["Product", "Qty", "Price", f"Gct ({self.gct_rate:.0f}%)", "Total", "Remove"]
        )
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, w in enumerate([80, 100, 110, 100, 70], start=1):
            self.cart_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.cart_table.setColumnWidth(col, w)
        self.cart_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setShowGrid(False)
        self.cart_table.setStyleSheet("""
            QTableWidget {
                background-color: #0d1117; color: #ffffff;
                border: none; border-radius: 8px; font-size: 13px;
            }
            QHeaderView::section {
                background-color: #161b22; color: #8b949e;
                font-size: 13px; font-weight: 700;
                padding: 8px; border: none;
                border-bottom: 1px solid #30363d;
            }
            QTableWidget::item { padding: 6px 8px; border: none; }
            QTableWidget::item:selected { background-color: #21262d; }
            QScrollBar:vertical { background: #161b22; width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #30363d; border-radius: 3px; }
        """)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        clear_btn = QPushButton("🗑  Clear Cart")
        clear_btn.setFixedHeight(40)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(self._action_btn_style())
        clear_btn.clicked.connect(self._clear_cart)

        btn_row.addWidget(clear_btn)
        btn_row.addStretch()

        layout.addLayout(header)
        layout.addWidget(self.results_list)
        layout.addWidget(self.cart_table, stretch=1)
        layout.addLayout(btn_row)
        return panel

    # ── Right panel — totals & cart selector ──────────────────────────
    def _build_right_panel(self):
        panel = QFrame()
        panel.setFixedWidth(170)
        panel.setStyleSheet("background-color: #161b22; border-radius: 10px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Cart selector section at top
        cart_section = QFrame()
        cart_section.setStyleSheet(f"background-color: {CART_COLORS[self.active_cart]}; border: none;")
        cart_layout = QVBoxLayout(cart_section)
        cart_layout.setContentsMargins(14, 14, 14, 14)
        cart_layout.setSpacing(10)

        self.cart_number_label = QLabel(f"Cart {self.active_cart + 1}")
        self.cart_number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cart_number_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 700; background: transparent;")

        # Cart navigation buttons
        nav_row = QHBoxLayout()
        nav_row.setSpacing(6)

        prev_btn = QPushButton("←")
        prev_btn.setFixedSize(36, 36)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setStyleSheet(self._arrow_btn_style())
        prev_btn.clicked.connect(self._prev_cart)

        next_btn = QPushButton("→")
        next_btn.setFixedSize(36, 36)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setStyleSheet(self._arrow_btn_style())
        next_btn.clicked.connect(self._next_cart)

        nav_row.addWidget(prev_btn)
        nav_row.addStretch()
        nav_row.addWidget(next_btn)

        cart_layout.addWidget(self.cart_number_label)
        cart_layout.addLayout(nav_row)
        self.cart_section = cart_section

        layout.addWidget(cart_section)
        layout.addStretch()

        def block(title, attr, big=False):
            f = QFrame()
            f.setStyleSheet(f"background-color: {CART_COLORS[self.active_cart]}; border: none;")
            bl = QVBoxLayout(f)
            bl.setContentsMargins(14, 14, 14, 14)
            bl.setSpacing(4)
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setStyleSheet("background-color: rgba(255,255,255,0.15); max-height:1px; border:none;")
            t = QLabel(title)
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setStyleSheet(f"color:#e2e8f0; font-size:{'15' if big else '13'}px; background:transparent;")
            v = QLabel("$0.00")
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.setStyleSheet(
                f"color:#ffffff; font-size:{'22' if big else '14'}px; "
                f"font-weight:{'800' if big else '500'}; background:transparent;"
            )
            bl.addWidget(line)
            bl.addWidget(t)
            bl.addWidget(v)
            setattr(self, attr, v)
            setattr(self, f"{attr}_frame", f)
            return f

        # Change display — shown after each transaction, hidden initially
        change_frame = QFrame()
        change_frame.setStyleSheet("background-color: #0d1117; border: none;")
        change_layout = QVBoxLayout(change_frame)
        change_layout.setContentsMargins(14, 14, 14, 14)
        change_layout.setSpacing(4)
        change_line = QFrame()
        change_line.setFrameShape(QFrame.Shape.HLine)
        change_line.setStyleSheet("background-color: rgba(255,255,255,0.08); max-height:1px; border:none;")
        change_title = QLabel("Last Change")
        change_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        change_title.setStyleSheet("color:#8b949e; font-size:11px; background:transparent; text-transform:uppercase; letter-spacing:1px;")
        self.change_display = QLabel("")
        self.change_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.change_display.setStyleSheet("color:#3fb950; font-size:22px; font-weight:800; background:transparent;")
        change_layout.addWidget(change_line)
        change_layout.addWidget(change_title)
        change_layout.addWidget(self.change_display)
        change_frame.setVisible(False)
        self.change_display_frame = change_frame

        layout.addWidget(change_frame)
        layout.addWidget(block("Subtotal", "subtotal_label"))
        layout.addWidget(block(f"Gct ({self.gct_rate:.2f}%)", "gct_label"))
        layout.addWidget(block("Discount", "discount_label"))
        layout.addWidget(block("TOTAL", "total_label", big=True))
        return panel

    # ----------------------------------------------------------------
    # CLOCK
    # ----------------------------------------------------------------

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.setText(
            f"Date: {now.strftime('%B %d, %Y')}  |  Time: {now.strftime('%I:%M %p')}"
        )

    # ----------------------------------------------------------------
    # CART NAVIGATION
    # ----------------------------------------------------------------

    def _prev_cart(self):
        self.active_cart = (self.active_cart - 1) % self.MAX_CARTS
        self._switch_cart()

    def _next_cart(self):
        self.active_cart = (self.active_cart + 1) % self.MAX_CARTS
        self._switch_cart()

    def _switch_cart(self):
        self.cart_number_label.setText(f"Cart {self.active_cart + 1}")
        color = CART_COLORS[self.active_cart]
        self.cart_section.setStyleSheet(f"background-color: {color}; border: none;")
        self.subtotal_label_frame.setStyleSheet(f"background-color: {color}; border: none;")
        self.gct_label_frame.setStyleSheet(f"background-color: {color}; border: none;")
        self.discount_label_frame.setStyleSheet(f"background-color: {color}; border: none;")
        self.total_label_frame.setStyleSheet(f"background-color: {color}; border: none;")
        self.results_list.setVisible(False)
        self.search_input.clear()
        self._refresh_table()
        self._update_totals()

    @property
    def cart(self):
        return self.carts[self.active_cart]

    # ----------------------------------------------------------------
    # SEARCH & RESULTS NAVIGATION
    # ----------------------------------------------------------------

    def _search_key_press(self, event):
        if event.key() == Qt.Key.Key_Up:
            # Focus qty spinbox when up arrow is pressed
            self.qty_spinbox.setFocus()
            self.qty_spinbox.selectAll()
            return
        elif event.key() == Qt.Key.Key_Down:
            # Move to results list when down arrow is pressed
            if self.results_list.isVisible() and self.results_list.count() > 0:
                self.results_list.setCurrentRow(0)
                self.results_list.setFocus()
            return
        QLineEdit.keyPressEvent(self.search_input, event)

    def _results_key_press(self, event):
        if event.key() == Qt.Key.Key_Down:
            current = self.results_list.currentRow()
            if current < self.results_list.count() - 1:
                self.results_list.setCurrentRow(current + 1)
        elif event.key() == Qt.Key.Key_Up:
            current = self.results_list.currentRow()
            if current > 0:
                self.results_list.setCurrentRow(current - 1)
            elif current == 0:
                self.search_input.setFocus()
        elif event.key() == Qt.Key.Key_Return:
            if self.results_list.currentItem():
                self._add_from_results(self.results_list.currentItem())
        else:
            QListWidget.keyPressEvent(self.results_list, event)

    def _handle_search_enter(self):
        qty = self.qty_spinbox.value()
        text = self.search_input.text().strip()
        if not text:
            self._handle_checkout()
            return
        product = self._find_by_barcode(text)
        if product:
            self._add_to_cart(product, qty)
            self.search_input.clear()
            self.qty_spinbox.setValue(1)
            self.results_list.setVisible(False)
            self.search_input.setFocus()
            return
        results = self._search_by_name(text)
        if len(results) == 1:
            self._add_to_cart(results[0], qty)
            self.search_input.clear()
            self.qty_spinbox.setValue(1)
            self.results_list.setVisible(False)
            self.search_input.setFocus()
        else:
            self._show_results(results)

    def _find_by_barcode(self, barcode):
        conn = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.price, p.discount_level, p.gct_applicable
            FROM products p WHERE p.barcode = ?
        """, (barcode,))
        row = cursor.fetchone()
        conn.close()
        return row

    def _search_by_name(self, query):
        conn = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.price, p.discount_level, p.gct_applicable
            FROM products p
            WHERE (p.name LIKE ? OR p.brand LIKE ?)
            LIMIT 20
        """, (f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        conn.close()
        return rows

    def _show_results(self, results):
        self.results_list.clear()
        if not results:
            item = QListWidgetItem("  No products found")
            item.setForeground(QColor("#8b949e"))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.results_list.addItem(item)
        else:
            for row in results:
                pid, name, price, _, gct_applicable = row
                gct_tag = "  [GCT]" if gct_applicable else "  [No GCT]"
                item = QListWidgetItem(f"  {name}  —  ${price:.2f}{gct_tag}")
                item.setData(Qt.ItemDataRole.UserRole, row)
                self.results_list.addItem(item)
        self.results_list.setVisible(True)

    def _add_from_results(self, item):
        qty = self.qty_spinbox.value()
        product = item.data(Qt.ItemDataRole.UserRole)
        if product:
            self._add_to_cart(product, qty)
            self.search_input.clear()
            self.qty_spinbox.setValue(1)
            self.results_list.setVisible(False)
            self.search_input.setFocus()

    # ----------------------------------------------------------------
    # QUICK KEYS
    # ----------------------------------------------------------------

    def _add_quick_key(self, idx):
        qty = self.qty_spinbox.value()
        if idx < len(self.quick_keys):
            qk = self.quick_keys[idx]
            self._add_to_cart((
                qk["id"], qk["name"], qk["price"],
                qk.get("discount_level"), qk.get("gct_applicable", 1)
            ), qty)
            self.qty_spinbox.setValue(1)

    # ----------------------------------------------------------------
    # CART MANAGEMENT
    # ----------------------------------------------------------------

    def _add_to_cart(self, product, qty=1):
        pid, name, price, discount_level, gct_applicable = product
        gct   = round(price * (self.gct_rate / 100), 2) if gct_applicable else 0.0
        total = round((price + gct) * qty, 2)

        for item in self.cart:
            if item["id"] == pid:
                item["qty"]  += qty
                item["total"] = round((item["price"] + item["gct"]) * item["qty"], 2)
                self._refresh_table()
                self._update_totals()
                return

        self.cart.append({
            "id": pid, "name": name, "qty": qty,
            "price": price, "gct": gct, "total": total,
            "gct_applicable": gct_applicable,
        })
        self._refresh_table()
        self._update_totals()

    def _refresh_table(self):
        self.cart_table.setRowCount(len(self.cart))
        center = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        left   = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        for row, item in enumerate(self.cart):
            def cell(text, color="#ffffff", align=left):
                c = QTableWidgetItem(str(text))
                c.setForeground(QColor(color))
                c.setTextAlignment(align)
                return c
            self.cart_table.setItem(row, 0, cell(item["name"]))
            self.cart_table.setItem(row, 1, cell(item["qty"],                align=center))
            self.cart_table.setItem(row, 2, cell(f"${item['price']:.2f}", "#4493f8", center))
            self.cart_table.setItem(row, 3, cell(f"${item['gct'] * item['qty']:.2f}",   "#4493f8", center))
            self.cart_table.setItem(row, 4, cell(f"${item['total']:.2f}", "#4493f8", center))
            remove_btn = QPushButton("✕")
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent; color: #f85149;
                    border: 1.5px solid #f85149; border-radius: 4px;
                    font-size: 12px; font-weight: 700;
                }
                QPushButton:hover { background-color: #f85149; color: #fff; }
            """)
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.clicked.connect(lambda _, r=row: self._remove_from_cart(r))
            self.cart_table.setCellWidget(row, 5, remove_btn)
            self.cart_table.setRowHeight(row, 38)

    def _remove_from_cart(self, row):
        if 0 <= row < len(self.cart):
            self.cart.pop(row)
            self._refresh_table()
            self._update_totals()

    def _clear_cart(self):
        self.carts[self.active_cart] = []
        self._refresh_table()
        self._update_totals()

    def _update_totals(self):
        subtotal = sum(item["price"] * item["qty"] for item in self.cart)
        gct      = sum(item["gct"]   * item["qty"] for item in self.cart)
        discount = 0.0
        total    = subtotal + gct - discount
        self.subtotal_label.setText(f"${subtotal:.2f}")
        self.gct_label.setText(f"${gct:.2f}")
        self.discount_label.setText(f"${discount:.2f}")
        self.total_label.setText(f"${total:.2f}")

    # ----------------------------------------------------------------
    # CHECKOUT & VOID
    # ----------------------------------------------------------------

    def _handle_checkout(self):
        if not self.cart:
            return
        from ui.checkout_dialog import CheckoutDialog
        dialog = CheckoutDialog(self.cart, self.user_id, self.full_name, self.gct_rate, self)
        if dialog.exec():
            # Show change due on the dashboard for the customer to see
            self._show_change(dialog.change_given)
            self._clear_cart()
            self.search_input.setFocus()

    def _show_change(self, change):
        """Display the change from the last transaction above the subtotal."""
        self.change_display.setText(f"${change:.2f}")
        self.change_display_frame.setVisible(True)

    def _void_transaction(self):
        if not self.cart:
            return
        from ui.dialogs import VoidDialog
        VoidDialog(self).exec()

    # ----------------------------------------------------------------
    # LOGOUT
    # ----------------------------------------------------------------

    def _handle_logout(self):
        from PyQt6.QtWidgets import QMessageBox
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
    # DATABASE HELPERS
    # ----------------------------------------------------------------

    def _load_gct_rate(self):
        conn = get_business_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT tax_percent FROM business_info WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] else 16.5

    def _load_quick_keys(self):
        conn = get_products_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.price, p.discount_level, p.gct_applicable
            FROM products p
            INNER JOIN quick_keys qk ON qk.product_id = p.id
            ORDER BY qk.key_number ASC LIMIT 8
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "name": r[1], "price": r[2],
             "discount_level": r[3], "gct_applicable": r[4]}
            for r in rows
        ]

    # ----------------------------------------------------------------
    # STYLE HELPERS
    # ----------------------------------------------------------------

    def _center_on_screen(self):
        screen = self.screen().availableGeometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2
        )

    def _fkey_style(self, disabled=False):
        if disabled:
            return """QPushButton {
                background-color: #21262d; color: #484f58;
                border: 1px solid #30363d; border-radius: 8px; font-size: 10px;
            }"""
        return """QPushButton {
                background-color: #21262d; color: #ffffff;
                border: 1px solid #30363d; border-radius: 8px;
                font-size: 10px; text-align: center;
            }
            QPushButton:hover   { background-color: #1a56db; border-color: #1a56db; }
            QPushButton:pressed { background-color: #1145b0; }"""

    def _arrow_btn_style(self):
        return """QPushButton {
                background-color: rgba(255,255,255,0.1); color: #ffffff;
                border: 1.5px solid rgba(255,255,255,0.2); border-radius: 18px;
                font-size: 16px; font-weight: 700;
            }
            QPushButton:hover   { background-color: rgba(255,255,255,0.2); }
            QPushButton:pressed { background-color: rgba(255,255,255,0.3); }"""

    def _action_btn_style(self):
        return """QPushButton {
                background-color: #21262d; color: #ffffff;
                border: 1.5px solid #30363d; border-radius: 20px;
                font-size: 13px; font-weight: 600; padding: 0 20px;
            }
            QPushButton:hover   { background-color: #30363d; }
            QPushButton:pressed { background-color: #484f58; }"""
