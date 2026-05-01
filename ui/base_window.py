"""
ui/base_window.py
Base window class for all protected windows in the POS system.
Blocks the X button; provides global zoom via Ctrl+±/0 and ZoomWidget.
"""

import json
import os
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QShortcut, QKeySequence


# ── Zoom state ────────────────────────────────────────────────────────────────

_FONT_SCALE   = 1.0
_BASE_FONT_SIZE = 13  # pts
_ZOOM_FILE    = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".pos_zoom"
)

def _load_zoom():
    global _FONT_SCALE
    try:
        with open(_ZOOM_FILE) as f:
            val = float(json.load(f).get("scale", 1.0))
            _FONT_SCALE = max(0.6, min(2.0, val))
    except Exception:
        _FONT_SCALE = 1.0

def _save_zoom():
    try:
        with open(_ZOOM_FILE, "w") as f:
            json.dump({"scale": _FONT_SCALE}, f)
    except Exception:
        pass

def _do_zoom(direction):
    """
    Shared zoom logic. direction: +1=in, -1=out, 0=reset.
    Exported so ZoomWidget can call it directly.
    """
    global _FONT_SCALE
    if direction == 0:
        _FONT_SCALE = 1.0
    elif direction > 0:
        _FONT_SCALE = min(_FONT_SCALE + 0.1, 2.0)
    else:
        _FONT_SCALE = max(_FONT_SCALE - 0.1, 0.6)

    _save_zoom()

    new_size = max(8, round(_BASE_FONT_SIZE * _FONT_SCALE))
    app = QApplication.instance()
    if app:
        font = app.font()
        font.setPointSize(new_size)
        app.setFont(font)
        # Re-apply full QSS so pixel sizes derived from font update correctly
        from ui.theme import ThemeManager
        ThemeManager.instance().reapply()

# Load saved zoom at import time
_load_zoom()


# ── Base window ───────────────────────────────────────────────────────────────

class BaseWindow(QMainWindow):
    """
    QMainWindow that:
    - Blocks accidental close via the X button
    - Provides Ctrl++/Ctrl+-/Ctrl+0 global zoom shortcuts
    - Applies saved zoom level on construction
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_zoom_shortcuts()
        # Apply saved zoom to the app font immediately
        self._apply_saved_zoom()

    def _apply_saved_zoom(self):
        new_size = max(8, round(_BASE_FONT_SIZE * _FONT_SCALE))
        app = QApplication.instance()
        if app:
            font = app.font()
            if font.pointSize() != new_size:
                font.setPointSize(new_size)
                app.setFont(font)

    def _setup_zoom_shortcuts(self):
        zoom_in  = QShortcut(QKeySequence("Ctrl++"), self)
        zoom_in2 = QShortcut(QKeySequence("Ctrl+="), self)
        zoom_out = QShortcut(QKeySequence("Ctrl+-"), self)
        zoom_rst = QShortcut(QKeySequence("Ctrl+0"), self)
        zoom_in.activated.connect(lambda: self._zoom(+1))
        zoom_in2.activated.connect(lambda: self._zoom(+1))
        zoom_out.activated.connect(lambda: self._zoom(-1))
        zoom_rst.activated.connect(lambda: self._zoom(0))

    def _zoom(self, direction):
        _do_zoom(direction)
        # Refresh any ZoomWidget in this window's topbar
        for widget in self.findChildren(type(None).__class__):
            pass
        pct = round(_FONT_SCALE * 100)
        orig = self.windowTitle()
        self.setWindowTitle(f"{orig}  [{pct}%]")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.setWindowTitle(orig))
        # Refresh all ZoomWidgets
        try:
            from ui.theme_toggle import ZoomWidget
            for w in self.findChildren(ZoomWidget):
                w._refresh_label()
        except Exception:
            pass

    def closeEvent(self, event):
        warning = QMessageBox(self)
        warning.setWindowTitle("Cannot Close")
        warning.setText("You cannot close this window using the X button.")
        warning.setInformativeText(
            "Please use the Logout or Exit option from the dashboard."
        )
        warning.setIcon(QMessageBox.Icon.Warning)
        warning.setStandardButtons(QMessageBox.StandardButton.Ok)
        warning.exec()
        event.ignore()

    def force_close(self):
        self.closeEvent = lambda event: event.accept()
        self.close()
