"""
ui/checkout_dialog.py
Checkout dialog — cash payment, change calculation, saves transaction to database.
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QDoubleValidator
from db import get_transactions_conn


class CheckoutDialog(QDialog):
    """
    Cash checkout dialog.
    Shows order summary, accepts cash input, calculates change,
    and saves the transaction to the database on confirmation.
    """

    def __init__(self, cart, user_id, cashier_name, gct_rate, parent=None):
        super().__init__(parent)
        self.cart         = cart
        self.user_id      = user_id
        self.cashier_name = cashier_name
        self.gct_rate     = gct_rate

        # Calculate totals from cart
        self.subtotal    = round(sum(i["price"] * i["qty"] for i in cart), 2)
        self.gct_total   = round(sum(i["gct"]   * i["qty"] for i in cart), 2)
        self.discount    = 0.0
        self.total       = round(self.subtotal + self.gct_total - self.discount, 2)
        self.change_given = 0.0  # set after payment confirmed, read by dashboard

        self.setWindowTitle("Checkout")
        self.setFixedSize(400, 480)
        self.setModal(True)
        self.setStyleSheet("background-color: #161b22;")
        self._build_ui()
        self._update_change()

    # ----------------------------------------------------------------
    # UI CONSTRUCTION
    # ----------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # ── Title ────────────────────────────────────────────────────
        title = QLabel("Checkout")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color: #ffffff; font-size: 20px; font-weight: 700;"
        )

        # ── Order summary ─────────────────────────────────────────────
        summary = QFrame()
        summary.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border-radius: 8px;
            }
        """)
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setSpacing(6)

        summary_layout.addWidget(self._summary_row("Subtotal",  f"${self.subtotal:.2f}"))
        summary_layout.addWidget(self._summary_row(
            f"GCT ({self.gct_rate:.1f}%)", f"${self.gct_total:.2f}"
        ))
        summary_layout.addWidget(self._summary_row("Discount",  f"${self.discount:.2f}"))
        summary_layout.addWidget(self._divider())
        summary_layout.addWidget(self._summary_row(
            "TOTAL", f"${self.total:.2f}", bold=True
        ))

        # ── Cash tendered ─────────────────────────────────────────────
        cash_label = QLabel("Cash Tendered")
        cash_label.setStyleSheet(
            "color: #8b949e; font-size: 12px; "
            "text-transform: uppercase; letter-spacing: 1px;"
        )

        cash_row = QHBoxLayout()
        dollar = QLabel("$")
        dollar.setStyleSheet("color: #8b949e; font-size: 20px;")

        self.cash_input = QLineEdit()
        self.cash_input.setPlaceholderText("0.00")
        self.cash_input.setFixedHeight(50)
        self.cash_input.setValidator(QDoubleValidator(0, 999999, 2))
        self.cash_input.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #ffffff;
                border: 1.5px solid #1a56db;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 22px;
                font-weight: 700;
            }
            QLineEdit:focus { border-color: #4493f8; }
        """)
        self.cash_input.textChanged.connect(self._update_change)
        self.cash_input.returnPressed.connect(self._confirm_payment)

        cash_row.addWidget(dollar)
        cash_row.addWidget(self.cash_input)

        # ── Change due ────────────────────────────────────────────────
        change_frame = QFrame()
        change_frame.setStyleSheet("""
            QFrame { background-color: #0d1117; border-radius: 8px; }
        """)
        change_layout = QHBoxLayout(change_frame)
        change_layout.setContentsMargins(16, 14, 16, 14)

        change_lbl = QLabel("Change Due")
        change_lbl.setStyleSheet("color: #8b949e; font-size: 14px;")

        self.change_label = QLabel("$0.00")
        self.change_label.setStyleSheet(
            "color: #3fb950; font-size: 22px; font-weight: 800;"
        )
        self.change_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        change_layout.addWidget(change_lbl)
        change_layout.addWidget(self.change_label)

        # ── Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(46)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #ffffff;
                border: 1.5px solid #30363d;
                border-radius: 23px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = QPushButton("Confirm Payment")
        self.confirm_btn.setFixedHeight(46)
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a56db;
                color: #ffffff;
                border: none;
                border-radius: 23px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover    { background-color: #1145b0; }
            QPushButton:pressed  { background-color: #0e3a8c; }
            QPushButton:disabled {
                background-color: #21262d;
                color: #484f58;
            }
        """)
        self.confirm_btn.clicked.connect(self._confirm_payment)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.confirm_btn, stretch=1)

        # ── Assemble ──────────────────────────────────────────────────
        layout.addWidget(title)
        layout.addWidget(summary)
        layout.addWidget(cash_label)
        layout.addLayout(cash_row)
        layout.addWidget(change_frame)
        layout.addLayout(btn_row)

        # Focus cash input immediately
        self.cash_input.setFocus()

    # ----------------------------------------------------------------
    # HELPERS
    # ----------------------------------------------------------------

    def _summary_row(self, label, value, bold=False):
        row = QFrame()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {'#ffffff' if bold else '#8b949e'}; "
            f"font-size: {'16' if bold else '13'}px; "
            f"font-weight: {'700' if bold else '400'}; background: transparent;"
        )
        val = QLabel(value)
        val.setStyleSheet(
            f"color: {'#ffffff' if bold else '#4493f8'}; "
            f"font-size: {'16' if bold else '13'}px; "
            f"font-weight: {'700' if bold else '400'}; background: transparent;"
        )
        val.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(lbl)
        layout.addWidget(val)
        return row

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(
            "background-color: #30363d; max-height: 1px; border: none;"
        )
        return line

    # ----------------------------------------------------------------
    # LOGIC
    # ----------------------------------------------------------------

    def _update_change(self):
        """Recalculate change due as cash amount is typed."""
        try:
            cash = float(self.cash_input.text() or "0")
        except ValueError:
            cash = 0.0

        change = round(cash - self.total, 2)

        if cash == 0.0:
            self.change_label.setText("$0.00")
            self.change_label.setStyleSheet(
                "color: #8b949e; font-size: 22px; font-weight: 800;"
            )
            self.confirm_btn.setEnabled(False)
        elif change < 0:
            # Not enough cash — show deficit in red
            self.change_label.setText(f"-${abs(change):.2f}")
            self.change_label.setStyleSheet(
                "color: #f85149; font-size: 22px; font-weight: 800;"
            )
            self.confirm_btn.setEnabled(False)
        else:
            # Enough cash — show change in green
            self.change_label.setText(f"${change:.2f}")
            self.change_label.setStyleSheet(
                "color: #3fb950; font-size: 22px; font-weight: 800;"
            )
            self.confirm_btn.setEnabled(True)

    def _confirm_payment(self):
        """Confirm payment with validation. Show warning if insufficient cash."""
        try:
            cash = float(self.cash_input.text() or "0")
        except ValueError:
            QMessageBox.warning(
                self, "Invalid Amount",
                "Please enter a valid cash amount."
            )
            return

        if cash < self.total:
            QMessageBox.warning(
                self, "Insufficient Cash",
                f"Cash amount (${cash:.2f}) is less than total (${self.total:.2f}).\n\n"
                f"Shortage: ${self.total - cash:.2f}"
            )
            self.cash_input.selectAll()
            self.cash_input.setFocus()
            return

        change = round(cash - self.total, 2)
        self.change_given = change

        # Save to database
        success = self._save_transaction(cash, change)
        if success:
            # Show success message with change
            msg = QMessageBox(self)
            msg.setWindowTitle("Payment Complete")
            msg.setText(f"Payment accepted!")
            msg.setInformativeText(
                f"Cash:    ${cash:.2f}\n"
                f"Total:   ${self.total:.2f}\n"
                f"Change:  ${change:.2f}"
            )
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStyleSheet("background-color: #161b22; color: #ffffff;")
            msg.exec()
            self.accept()
        else:
            QMessageBox.critical(
                self, "Error",
                "Failed to save transaction. Please try again."
            )

    def _save_transaction(self, cash_tendered, change):
        """Save the completed transaction and all its items to the database."""
        try:
            conn = get_transactions_conn()
            cursor = conn.cursor()
            now  = datetime.now()
            date = now.strftime("%Y-%m-%d")
            time = now.strftime("%H:%M:%S")

            # Get or create session for this cashier
            session_id = self._get_or_create_session(cursor)

            # Insert transaction with cashier name snapshot
            cursor.execute("""
                INSERT INTO transactions
                    (session_id, cashier_id, cashier_name, date, time,
                     subtotal, tax_amount, total, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed')
            """, (
                session_id, self.user_id, self.cashier_name,
                date, time, self.subtotal, self.gct_total, self.total
            ))
            transaction_id = cursor.lastrowid

            # Insert each cart item with snapshots
            for item in self.cart:
                cursor.execute("""
                    INSERT INTO transaction_items
                        (transaction_id, product_id,
                         product_name_snapshot, barcode_snapshot,
                         unit_price_snapshot, quantity,
                         gct_applicable, discount_applied, line_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction_id,
                    item.get("id"),
                    item["name"],
                    item.get("barcode", ""),
                    item["price"],
                    item["qty"],
                    item.get("gct_applicable", 1),
                    item.get("discount_applied", 0.0),
                    round(item["price"] * item["qty"], 2)
                ))

            # Update cashier session total
            cursor.execute("""
                UPDATE sessions
                SET total_sales = total_sales + ?
                WHERE id = ?
            """, (self.total, session_id))

            # Update active cashing_session totals (supervisor trading period)
            discount_total = sum(item.get("discount_applied", 0.0) * item["qty"]
                                 for item in self.cart)
            cursor.execute("""
                UPDATE cashing_sessions
                SET total_sales       = total_sales       + ?,
                    total_gct         = total_gct         + ?,
                    total_discount    = total_discount    + ?,
                    transaction_count = transaction_count + 1
                WHERE status = 'open'
                ORDER BY id DESC
                LIMIT 1
            """, (self.total, self.gct_total, discount_total))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Transaction save error: {e}")
            return False

    def _get_or_create_session(self, cursor):
        """Get the open session for this cashier or create a new one."""
        cursor.execute("""
            SELECT id FROM sessions
            WHERE cashier_id = ? AND ended_at IS NULL
            ORDER BY started_at DESC LIMIT 1
        """, (self.user_id,))
        row = cursor.fetchone()
        if row:
            return row[0]

        # No open session — create one
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO sessions (cashier_id, cashier_name, started_at, total_sales)
            VALUES (?, ?, ?, 0.0)
        """, (self.user_id, self.cashier_name, now))
        return cursor.lastrowid
