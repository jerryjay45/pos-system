"""
printing/normal_printer.py
Prints receipts to a normal (A4/Letter/Legal) printer using
PyQt6's QPrinter and QPainter.

Receipt prints compact at the top of the page like a real receipt,
remaining page space is left blank.
"""

from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo, QPrintDialog
from PyQt6.QtGui import QPainter, QFont, QFontMetrics
from PyQt6.QtCore import Qt, QRect


# ── Paper size map ────────────────────────────────────────────────────────────

_PAPER_SIZES = {
    "A4":     QPrinter.PaperSize.A4,
    "Letter": QPrinter.PaperSize.Letter,
    "Legal":  QPrinter.PaperSize.Legal,
}


def _get_printer_settings():
    """Read normal printer settings from business.db."""
    try:
        from db import get_business_conn
        conn = get_business_conn()
        row  = conn.execute("""
            SELECT paper_size, normal_printer_name
            FROM business_info WHERE id = 1
        """).fetchone()
        conn.close()
        if row:
            return {
                "paper_size":   row[0] or "A4",
                "printer_name": row[1] or "",
            }
    except Exception:
        pass
    return {"paper_size": "A4", "printer_name": ""}


def _setup_printer(settings, show_dialog=False, parent=None):
    """
    Configure and return a QPrinter.
    If show_dialog=True, presents a print dialog for the user to choose printer.
    Returns (QPrinter, True) on success, (None, False) if user cancelled.
    """
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setColorMode(QPrinter.ColorMode.GrayScale)
    printer.setOrientation(QPrinter.Orientation.Portrait)

    paper_size = _PAPER_SIZES.get(settings.get("paper_size", "A4"),
                                  QPrinter.PaperSize.A4)
    printer.setPaperSize(paper_size)

    # Try to use the saved printer name
    saved_name = settings.get("printer_name", "")
    if saved_name:
        for info in QPrinterInfo.availablePrinters():
            if info.printerName() == saved_name:
                printer.setPrinterName(saved_name)
                break

    if show_dialog:
        dialog = QPrintDialog(printer, parent)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return None, False

    return printer, True


def print_text_normal(text, show_dialog=False, parent=None):
    """
    Print formatted receipt text to a normal printer.

    Args:
        text:        str — full formatted receipt text
        show_dialog: bool — show print dialog (True for reprint, False for auto)
        parent:      QWidget parent for the dialog

    Returns:
        (True, None) on success
        (False, error_message) on failure
    """
    settings       = _get_printer_settings()
    printer, ok    = _setup_printer(settings, show_dialog=show_dialog, parent=parent)

    if not ok:
        return False, "Print cancelled"
    if printer is None:
        return False, "No printer available"

    try:
        painter = QPainter()
        if not painter.begin(printer):
            return False, "Failed to start painter"

        # Monospace font — matches thermal receipt look
        font = QFont("Courier New", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        painter.setFont(font)

        fm          = QFontMetrics(font)
        line_height = fm.height() + 2
        page_rect   = printer.pageRect(QPrinter.Unit.DevicePixel)

        x = int(page_rect.left()) + 20
        y = int(page_rect.top())  + 20

        lines = text.split("\n")
        for line in lines:
            # Wrap long lines
            if fm.horizontalAdvance(line) > page_rect.width() - 40:
                # Simple truncation for receipt text (shouldn't happen at 60-col)
                line = line[:80]

            painter.drawText(x, y + fm.ascent(), line)
            y += line_height

            # New page if we overflow (very long session reports)
            if y + line_height > page_rect.bottom() - 20:
                printer.newPage()
                y = int(page_rect.top()) + 20

        painter.end()
        return True, None

    except Exception as e:
        try:
            painter.end()
        except Exception:
            pass
        return False, str(e)


def get_available_printers():
    """Return list of available printer names on this system."""
    return [info.printerName() for info in QPrinterInfo.availablePrinters()]


def get_default_printer():
    """Return the system default printer name."""
    info = QPrinterInfo.defaultPrinter()
    return info.printerName() if info else ""
