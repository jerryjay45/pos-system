"""
printing/print_manager.py
Single entry point for all receipt printing in Merchant Retail POS.

Priority logic:
  1. Use configured default printer (thermal / normal / auto)
  2. If 'auto': try thermal first, fall back to normal silently
  3. On reprint: always show a dialog asking printer type

Public API:
    print_receipt(transaction_id, cash_tendered, change, parent=None)
    print_session(session_id, parent=None)
    print_void(transaction_id, reason, supervisor_name, parent=None)
    print_refund(transaction_id, refund_items, refund_total, reason,
                 supervisor_name, parent=None)
    reprint_receipt(transaction_id, parent=None)   ← shows printer dialog
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup, QRadioButton, QFrame
)
from PyQt6.QtCore import Qt

from printing.receipt_builder import (
    build_sale_receipt, build_void_receipt,
    build_refund_receipt, build_session_receipt,
    get_business_info,
)
from printing.formatter import (
    format_sale, format_void, format_refund, format_session,
    THERMAL_WIDTH, NORMAL_WIDTH,
)


# ── Printer type constants ────────────────────────────────────────────────────

THERMAL = "thermal"
NORMAL  = "normal"
AUTO    = "auto"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_default_printer_type():
    """Read configured default printer type from business.db."""
    biz = get_business_info()
    return biz.get("printer_type", AUTO)


def _send_to_thermal(text):
    """Send text to thermal/impact printer. Returns (ok, error)."""
    try:
        from printing.thermal_printer import print_text_thermal
        return print_text_thermal(text)
    except Exception as e:
        return False, str(e)


def _send_to_normal(text, show_dialog=False, parent=None):
    """Send text to normal printer. Returns (ok, error)."""
    try:
        from printing.normal_printer import print_text_normal
        return print_text_normal(text, show_dialog=show_dialog, parent=parent)
    except Exception as e:
        return False, str(e)


def _dispatch(text, printer_type, show_dialog=False, parent=None):
    """
    Send formatted text to the appropriate printer.
    Returns (ok, error_message).
    """
    if printer_type == THERMAL:
        ok, err = _send_to_thermal(text)
        if not ok:
            # Fall back to normal silently
            ok, err = _send_to_normal(text, show_dialog=False, parent=parent)
        return ok, err

    elif printer_type == NORMAL:
        return _send_to_normal(text, show_dialog=show_dialog, parent=parent)

    else:  # AUTO
        ok, err = _send_to_thermal(text)
        if ok:
            return True, None
        # Thermal not available — fall back to normal silently
        return _send_to_normal(text, show_dialog=False, parent=parent)


# ── Printer selection dialog (for reprint) ────────────────────────────────────

class _PrinterSelectDialog(QDialog):
    """
    Simple dialog asking the user to choose thermal or normal printer.
    Shown only on reprint, not on automatic print.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Printer")
        self.setFixedSize(320, 180)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.choice = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        lbl = QLabel("Print receipt to:")
        lbl.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(lbl)

        self._thermal_rb = QRadioButton("Thermal / Impact Printer  (TM-U220)")
        self._normal_rb  = QRadioButton("Normal Printer  (A4 / Letter / Legal)")
        self._thermal_rb.setChecked(True)

        group = QButtonGroup(self)
        group.addButton(self._thermal_rb)
        group.addButton(self._normal_rb)

        layout.addWidget(self._thermal_rb)
        layout.addWidget(self._normal_rb)
        layout.addStretch()

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.clicked.connect(self.reject)

        print_btn = QPushButton("Print")
        print_btn.setFixedHeight(32)
        print_btn.setDefault(True)
        print_btn.clicked.connect(self._on_print)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(print_btn)
        layout.addLayout(btn_row)

    def _on_print(self):
        self.choice = THERMAL if self._thermal_rb.isChecked() else NORMAL
        self.accept()


# ── Public API ────────────────────────────────────────────────────────────────

def print_receipt(transaction_id, cash_tendered=0.0, change=0.0, parent=None):
    """
    Auto-print after a completed sale.
    Uses configured default printer. Falls back silently on failure.

    Returns (ok, error_message).
    """
    data = build_sale_receipt(transaction_id)
    if not data:
        return False, f"Transaction #{transaction_id} not found"

    data["cash_tendered"] = cash_tendered
    data["change"]        = change

    biz    = get_business_info()
    layout = biz.get("receipt_layout", "gct_column")
    ptype  = _get_default_printer_type()

    # Format for appropriate width
    width  = THERMAL_WIDTH if ptype != NORMAL else NORMAL_WIDTH
    text   = format_sale(data, layout=layout, width=width)

    return _dispatch(text, ptype, parent=parent)


def reprint_receipt(transaction_id, parent=None):
    """
    Reprint a past receipt — always shows a printer selection dialog.

    Returns (ok, error_message).
    """
    data = build_sale_receipt(transaction_id)
    if not data:
        return False, f"Transaction #{transaction_id} not found"

    # Ask user which printer
    dlg = _PrinterSelectDialog(parent)
    if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.choice:
        return False, "Cancelled"

    ptype  = dlg.choice
    biz    = get_business_info()
    layout = biz.get("receipt_layout", "gct_column")
    width  = THERMAL_WIDTH if ptype == THERMAL else NORMAL_WIDTH
    text   = format_sale(data, layout=layout, width=width)

    # Normal printer shows its own dialog too for paper/copies
    return _dispatch(text, ptype,
                     show_dialog=(ptype == NORMAL),
                     parent=parent)


def print_void(transaction_id, reason, supervisor_name, parent=None):
    """
    Print a void receipt after a transaction is voided.
    Uses configured default printer.
    """
    data = build_void_receipt(transaction_id, reason, supervisor_name)
    if not data:
        return False, f"Transaction #{transaction_id} not found"

    ptype = _get_default_printer_type()
    width = THERMAL_WIDTH if ptype != NORMAL else NORMAL_WIDTH
    text  = format_void(data, width=width)

    return _dispatch(text, ptype, parent=parent)


def print_refund(transaction_id, refund_items, refund_total,
                 reason, supervisor_name, parent=None):
    """
    Print a refund receipt after a refund is issued.
    Uses configured default printer.
    """
    data = build_refund_receipt(
        transaction_id, refund_items, refund_total, reason, supervisor_name
    )
    if not data:
        return False, f"Transaction #{transaction_id} not found"

    ptype = _get_default_printer_type()
    width = THERMAL_WIDTH if ptype != NORMAL else NORMAL_WIDTH
    text  = format_refund(data, width=width)

    return _dispatch(text, ptype, parent=parent)


def print_session(session_id, parent=None):
    """
    Print a session summary.
    Uses configured default printer.
    """
    data = build_session_receipt(session_id)
    if not data:
        return False, f"Session #{session_id} not found"

    ptype = _get_default_printer_type()
    width = THERMAL_WIDTH if ptype != NORMAL else NORMAL_WIDTH
    text  = format_session(data, width=width)

    return _dispatch(text, ptype, parent=parent)
