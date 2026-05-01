"""
ui/dialogs.py
Shared dialogs used across the POS system.

VoidDialog     — cashier requests a void (needs supervisor/manager authorisation)
QuickKeysDialog — supervisor/manager assigns F1-F8 quick keys
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QComboBox,
    QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from db import get_products_conn, get_users_conn, get_transactions_conn
from ui.theme import DARK as T


# ================================================================
# VOID DIALOG — cashier side
# Shows current cart, requires supervisor/manager password.
# On success caller should clear the cart.
# ================================================================

class VoidDialog(QDialog):
    """
    Cashier-facing void dialog.
    Displays the current cart and requires a supervisor or manager
    password to authorise the void.
    Sets self.authorised_by and self.authorised_by_id on success.
    """

    def __init__(self, cart, user_id, parent=None):
        super().__init__(parent)
        self.cart             = cart
        self.user_id          = user_id
        self.authorised_by    = None
        self.authorised_by_id = None

        self.setWindowTitle("Void Current Cart")
        self.setFixedSize(500, 540)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {T['BG_SURFACE']};")
        self._build_ui()

    # ----------------------------------------------------------------
    # UI
    # ----------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Title
        title = QLabel("⊘  Void Current Cart")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {T['RED']}; font-size: 18px; font-weight: 700;")

        subtitle = QLabel(
            "Supervisor or Manager authorisation is required to void this cart.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"color: {T['TEXT_SECONDARY']}; font-size: 12px;")

        # Cart summary
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Product", "Qty", "Price", "Total"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        for col, w in enumerate([60, 80, 80], start=1):
            self.table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, w)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setMaximumHeight(190)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {T['BG_BASE']}; color: {T['TEXT_PRIMARY']};
                border: none; border-radius: 8px; font-size: 12px;
            }}
            QHeaderView::section {{
                background-color: {T['BG_SURFACE']}; color: {T['TEXT_SECONDARY']};
                font-size: 11px; font-weight: 700; padding: 6px;
                border: none; border-bottom: 1px solid {T['BORDER']};
            }}
            QTableWidget::item {{ padding: 5px 8px; border: none;
                border-bottom: 1px solid {T['BORDER']}; }}
            QScrollBar:vertical {{ background: {T['BG_BASE']}; width: 5px; border-radius: 3px; }}
            QScrollBar::handle:vertical {{ background: {T['BORDER']}; border-radius: 3px; }}
        """)

        center = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        left   = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        self.table.setRowCount(len(self.cart))
        cart_total = 0.0

        for row, item in enumerate(self.cart):
            row_total   = round(item.get("unit_total", item["price"] + item.get("unit_gct", 0)) * item["qty"], 2)
            cart_total += row_total

            def cell(text, color=None, align=left):
                c = QTableWidgetItem(str(text))
                c.setForeground(QColor(color or T['TEXT_PRIMARY']))
                c.setTextAlignment(align)
                return c

            self.table.setItem(row, 0, cell(item["name"]))
            self.table.setItem(row, 1, cell(item["qty"],               align=center))
            self.table.setItem(row, 2, cell(f"${item['price']:.2f}",   T['BLUE_TEXT'], center))
            self.table.setItem(row, 3, cell(f"${row_total:.2f}",       T['BLUE_TEXT'], center))
            self.table.setRowHeight(row, 32)

        # Cart total row
        total_row = QHBoxLayout()
        total_row.addStretch()
        total_lbl = QLabel(f"Cart Total:   ${cart_total:.2f}")
        total_lbl.setStyleSheet(
            f"color: {T['TEXT_PRIMARY']}; font-size: 14px; font-weight: 700;")
        total_row.addWidget(total_lbl)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(
            f"background-color: {T['BORDER']}; max-height: 1px; border: none;")

        # Password field
        auth_lbl = QLabel("Supervisor / Manager Password")
        auth_lbl.setStyleSheet(
            f"color: {T['TEXT_SECONDARY']}; font-size: 12px;")

        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("Enter password to authorise void")
        self.pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pin_input.setFixedHeight(46)
        self.pin_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {T['BG_INPUT']}; color: {T['TEXT_PRIMARY']};
                border: 1.5px solid {T['BORDER']}; border-radius: 8px;
                padding: 0 14px; font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {T['RED']}; }}
        """)
        self.pin_input.returnPressed.connect(self._authorise)

        # Error label
        self.error_lbl = QLabel("")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_lbl.setStyleSheet(
            f"color: {T['RED']}; font-size: 12px; min-height: 16px;")

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(44)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T['BG_ELEVATED']}; color: {T['TEXT_PRIMARY']};
                border: 1.5px solid {T['BORDER']}; border-radius: 22px;
                font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {T['BG_OVERLAY']}; }}
        """)
        cancel_btn.clicked.connect(self.reject)

        void_btn = QPushButton("⊘  Authorise Void")
        void_btn.setFixedHeight(44)
        void_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        void_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T['RED_BG']}; color: {T['RED_TEXT']};
                border: 1px solid {T['RED']}; border-radius: 22px;
                font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover  {{ background-color: {T['RED']}; color: #fff; }}
            QPushButton:pressed{{ background-color: #b91c1c; color: #fff; }}
        """)
        void_btn.clicked.connect(self._authorise)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(void_btn, stretch=1)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.table)
        layout.addLayout(total_row)
        layout.addWidget(div)
        layout.addWidget(auth_lbl)
        layout.addWidget(self.pin_input)
        layout.addWidget(self.error_lbl)
        layout.addLayout(btn_row)

        self.pin_input.setFocus()

    # ----------------------------------------------------------------
    # AUTHORISATION
    # ----------------------------------------------------------------

    def _authorise(self):
        """Verify password belongs to a supervisor or manager."""
        import hashlib
        password = self.pin_input.text().strip()
        if not password:
            self.error_lbl.setText("Please enter a password.")
            return

        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        conn    = get_users_conn()
        cursor  = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, role FROM users
            WHERE password_hash = ?
              AND role IN ('supervisor', 'manager')
              AND is_active = 1
        """, (pw_hash,))
        auth_user = cursor.fetchone()
        conn.close()

        if not auth_user:
            self.error_lbl.setText(
                "Invalid password or insufficient permissions.")
            self.pin_input.clear()
            self.pin_input.setFocus()
            return

        self.authorised_by    = auth_user[1]
        self.authorised_by_id = auth_user[0]
        self.accept()


# ================================================================
# QUICK KEYS DIALOG — supervisor / manager
# Assign products to F1–F8 quick keys.
# ================================================================

class QuickKeysDialog(QDialog):
    """
    Assign products to F1–F8 cashier quick keys.
    Left panel shows current key assignments.
    Right panel shows product list with a key selector per row.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("F1–F8 Quick Key Assignment")
        self.setFixedSize(700, 540)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {T['BG_SURFACE']};")
        self._all_products   = []
        self._key_assignments = {}   # key_number(1-8) → product_id
        self._build_ui()
        self._load_data()

    # ----------------------------------------------------------------
    # UI
    # ----------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Title
        title = QLabel("⌨  F1–F8 Quick Key Assignment")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {T['TEXT_PRIMARY']}; font-size: 17px; font-weight: 700;")

        subtitle = QLabel(
            "Assign a product to each function key. "
            "Cashiers can add them to the cart with a single keypress.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"color: {T['TEXT_SECONDARY']}; font-size: 12px;")

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "🔍  Search product by name or barcode…")
        self.search_input.setFixedHeight(36)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {T['BG_INPUT']}; color: {T['TEXT_PRIMARY']};
                border: 1.5px solid {T['BORDER']}; border-radius: 18px;
                padding: 0 14px; font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {T['BORDER_FOCUS']}; }}
        """)
        self.search_input.textChanged.connect(self._filter_products)

        # Body
        body = QHBoxLayout()
        body.setSpacing(12)

        # ── Left: key assignment panel ────────────────────────────────
        left = QFrame()
        left.setFixedWidth(255)
        left.setStyleSheet(
            f"background-color: {T['BG_BASE']}; border-radius: 10px;")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(12, 12, 12, 12)
        left_lay.setSpacing(5)

        keys_lbl = QLabel("CURRENT ASSIGNMENTS")
        keys_lbl.setStyleSheet(
            f"color: {T['TEXT_MUTED']}; font-size: 10px; "
            f"font-weight: 700; letter-spacing: 1px;")
        left_lay.addWidget(keys_lbl)

        self.key_rows = {}
        for i in range(1, 9):
            row_frame = QFrame()
            row_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {T['BG_SURFACE']};
                    border-radius: 6px;
                    border: 0.5px solid {T['BORDER']};
                }}
            """)
            row_lay = QHBoxLayout(row_frame)
            row_lay.setContentsMargins(10, 6, 6, 6)
            row_lay.setSpacing(6)

            fkey_lbl = QLabel(f"F{i}")
            fkey_lbl.setFixedWidth(22)
            fkey_lbl.setStyleSheet(
                f"color: {T['ACCENT']}; font-size: 11px; "
                f"font-weight: 700; background: transparent;")

            name_lbl = QLabel("— unassigned —")
            name_lbl.setStyleSheet(
                f"color: {T['TEXT_FAINT']}; font-size: 12px; background: transparent;")

            clear_btn = QPushButton("✕")
            clear_btn.setFixedSize(22, 22)
            clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            clear_btn.setVisible(False)
            clear_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {T['RED']};
                    border: 1px solid {T['RED']}; border-radius: 4px;
                    font-size: 11px; font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: {T['RED']}; color: #fff;
                }}
            """)
            clear_btn.clicked.connect(lambda _, k=i: self._clear_key(k))

            row_lay.addWidget(fkey_lbl)
            row_lay.addWidget(name_lbl, stretch=1)
            row_lay.addWidget(clear_btn)

            self.key_rows[i] = {"name_lbl": name_lbl, "clear_btn": clear_btn}
            left_lay.addWidget(row_frame)

        left_lay.addStretch()

        # ── Right: product list ───────────────────────────────────────
        right = QFrame()
        right.setStyleSheet(
            f"background-color: {T['BG_BASE']}; border-radius: 10px;")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(12, 12, 12, 12)
        right_lay.setSpacing(6)

        prod_lbl = QLabel(
            "SELECT A KEY FROM THE DROPDOWN TO ASSIGN")
        prod_lbl.setStyleSheet(
            f"color: {T['TEXT_MUTED']}; font-size: 10px; "
            f"font-weight: 700; letter-spacing: 1px;")
        right_lay.addWidget(prod_lbl)

        self.product_table = QTableWidget()
        self.product_table.setColumnCount(3)
        self.product_table.setHorizontalHeaderLabels(
            ["Name", "Price", "Assign to Key"])
        self.product_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.product_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed)
        self.product_table.setColumnWidth(1, 75)
        self.product_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed)
        self.product_table.setColumnWidth(2, 110)
        self.product_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.product_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.setShowGrid(False)
        self.product_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent; color: {T['TEXT_PRIMARY']};
                border: none; font-size: 12px;
            }}
            QHeaderView::section {{
                background-color: {T['BG_BASE']}; color: {T['TEXT_SECONDARY']};
                font-size: 11px; font-weight: 700; padding: 6px;
                border: none; border-bottom: 1px solid {T['BORDER']};
            }}
            QTableWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {T['BORDER']};
            }}
            QTableWidget::item:selected {{ background-color: {T['ROW_SEL']}; }}
            QScrollBar:vertical {{
                background: {T['BG_BASE']}; width: 5px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {T['BORDER']}; border-radius: 3px;
            }}
        """)
        right_lay.addWidget(self.product_table)

        body.addWidget(left)
        body.addWidget(right, stretch=1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(42)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T['BG_ELEVATED']}; color: {T['TEXT_PRIMARY']};
                border: 1.5px solid {T['BORDER']}; border-radius: 21px;
                font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {T['BG_OVERLAY']}; }}
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("💾  Save Quick Keys")
        save_btn.setFixedHeight(42)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {T['ACCENT']}; color: {T['ACCENT_TEXT']};
                border: none; border-radius: 21px;
                font-size: 13px; font-weight: 700;
            }}
            QPushButton:hover  {{ background-color: {T['ACCENT_HOVER']}; }}
            QPushButton:pressed{{ background-color: {T['ACCENT_PRESS']}; }}
        """)
        save_btn.clicked.connect(self._save)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn, stretch=1)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.search_input)
        layout.addLayout(body, stretch=1)
        layout.addLayout(btn_row)

    # ----------------------------------------------------------------
    # DATA
    # ----------------------------------------------------------------

    def _load_data(self):
        conn   = get_products_conn()
        cursor = conn.cursor()

        # Current assignments
        cursor.execute("""
            SELECT qk.key_number, p.id, p.name, p.price
            FROM quick_keys qk
            JOIN products p ON p.id = qk.product_id
            ORDER BY qk.key_number
        """)
        for key_num, pid, name, price in cursor.fetchall():
            self._key_assignments[key_num] = pid
            r = self.key_rows[key_num]
            r["name_lbl"].setText(f"{name}  ${price:.2f}")
            r["name_lbl"].setStyleSheet(
                f"color: {T['TEXT_PRIMARY']}; font-size: 12px; background: transparent;")
            r["clear_btn"].setVisible(True)

        # All single products
        cursor.execute("""
            SELECT p.id, p.name, p.price, p.barcode
            FROM products p
            WHERE p.is_case = 0
            ORDER BY p.name
        """)
        self._all_products = cursor.fetchall()
        conn.close()
        self._populate_product_table(self._all_products)

    def _populate_product_table(self, products):
        self.product_table.setRowCount(len(products))
        center = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        left   = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

        for row, (pid, name, price, barcode) in enumerate(products):
            name_item = QTableWidgetItem(name)
            name_item.setForeground(QColor(T['TEXT_PRIMARY']))
            name_item.setTextAlignment(left)
            name_item.setData(Qt.ItemDataRole.UserRole, pid)

            price_item = QTableWidgetItem(f"${price:.2f}")
            price_item.setForeground(QColor(T['BLUE_TEXT']))
            price_item.setTextAlignment(center)
            price_item.setData(Qt.ItemDataRole.UserRole, pid)

            self.product_table.setItem(row, 0, name_item)
            self.product_table.setItem(row, 1, price_item)

            # Key selector combo
            combo = QComboBox()
            combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {T['BG_ELEVATED']}; color: {T['TEXT_PRIMARY']};
                    border: 1px solid {T['BORDER']}; border-radius: 6px;
                    padding: 2px 8px; font-size: 11px;
                }}
                QComboBox::drop-down {{ border: none; }}
                QComboBox QAbstractItemView {{
                    background: {T['BG_ELEVATED']}; color: {T['TEXT_PRIMARY']};
                    border: 1px solid {T['BORDER']};
                    selection-background-color: {T['ACCENT_SUBTLE']};
                    selection-color: {T['ACCENT']};
                }}
            """)
            combo.addItem("— key —", None)
            for k in range(1, 9):
                combo.addItem(f"F{k}", k)

            # Pre-select if already assigned
            for key_num, assigned_pid in self._key_assignments.items():
                if assigned_pid == pid:
                    idx = combo.findData(key_num)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                    break

            combo.currentIndexChanged.connect(
                lambda _, c=combo, p=pid: self._on_combo_changed(c, p))
            self.product_table.setCellWidget(row, 2, combo)
            self.product_table.setRowHeight(row, 36)

    def _filter_products(self, text):
        if not text:
            self._populate_product_table(self._all_products)
        else:
            t = text.lower()
            filtered = [
                p for p in self._all_products
                if t in p[1].lower() or t in p[3].lower()
            ]
            self._populate_product_table(filtered)

    # ----------------------------------------------------------------
    # ASSIGNMENT LOGIC
    # ----------------------------------------------------------------

    def _on_combo_changed(self, combo, product_id):
        key_num = combo.currentData()
        if key_num is None:
            return

        # Clear any previous assignment to this key
        old_pid = self._key_assignments.get(key_num)
        if old_pid and old_pid != product_id:
            for row in range(self.product_table.rowCount()):
                item = self.product_table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == old_pid:
                    c = self.product_table.cellWidget(row, 2)
                    if c:
                        c.blockSignals(True)
                        c.setCurrentIndex(0)
                        c.blockSignals(False)
                    break

        self._key_assignments[key_num] = product_id

        # Update left panel
        conn   = get_products_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, price FROM products WHERE id = ?", (product_id,))
        row_data = cursor.fetchone()
        conn.close()

        if row_data:
            name, price = row_data
            r = self.key_rows[key_num]
            r["name_lbl"].setText(f"{name}  ${price:.2f}")
            r["name_lbl"].setStyleSheet(
                f"color: {T['TEXT_PRIMARY']}; font-size: 12px; background: transparent;")
            r["clear_btn"].setVisible(True)

    def _clear_key(self, key_num):
        self._key_assignments.pop(key_num, None)
        r = self.key_rows[key_num]
        r["name_lbl"].setText("— unassigned —")
        r["name_lbl"].setStyleSheet(
            f"color: {T['TEXT_FAINT']}; font-size: 12px; background: transparent;")
        r["clear_btn"].setVisible(False)

        for row in range(self.product_table.rowCount()):
            c = self.product_table.cellWidget(row, 2)
            if c and c.currentData() == key_num:
                c.blockSignals(True)
                c.setCurrentIndex(0)
                c.blockSignals(False)

    # ----------------------------------------------------------------
    # SAVE
    # ----------------------------------------------------------------

    def _save(self):
        try:
            conn = get_products_conn()
            conn.execute("DELETE FROM quick_keys")
            for key_num, product_id in self._key_assignments.items():
                conn.execute(
                    "INSERT INTO quick_keys (key_number, product_id) VALUES (?,?)",
                    (key_num, product_id))
            conn.commit()
            conn.close()
            QMessageBox.information(
                self, "Saved",
                "Quick key assignments saved!\n\n"
                "Cashiers will see the updated keys on their next login.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")
