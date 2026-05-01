"""
ui/theme_toggle.py
ZoomWidget — visible zoom control for the topbar.
Replaces the old ThemeToggleButton (light mode removed).

Usage (drop-in replacement for ThemeToggleButton):
    from ui.theme_toggle import ZoomWidget
    layout.addWidget(ZoomWidget(self._app))

The old ThemeToggleButton name is kept as an alias so existing
import lines still work without changing dashboards.
"""

from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from ui.theme import ThemeManager


_BTN = """
    QPushButton {{
        background-color: {bg};
        color: {fg};
        border: 1.5px solid {border};
        border-radius: 6px;
        font-size: {fs}px;
        font-weight: 700;
        min-width: {w}px;
        min-height: 28px;
        padding: 0 6px;
    }}
    QPushButton:hover {{
        background-color: #f59e0b;
        color: #0a0400;
        border-color: #f59e0b;
    }}
    QPushButton:pressed {{
        background-color: #d97706;
    }}
"""


class ZoomWidget(QWidget):
    """
    Compact +/− zoom control.
    Shows current zoom level as a percentage between the two buttons.
    Ctrl++ / Ctrl+- / Ctrl+0 still work via base_window shortcuts.
    """

    def __init__(self, app=None, parent=None):
        super().__init__(parent)
        self._app = app
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        v = ThemeManager.instance().palette
        btn_style = _BTN.format(
            bg=v["TOGGLE_BG"], fg=v["TOGGLE_TEXT"],
            border=v["TOGGLE_BORDER"], fs=13, w=28
        )

        self._minus = QPushButton("−")
        self._minus.setFixedSize(28, 28)
        self._minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._minus.setToolTip("Zoom out  (Ctrl+−)")
        self._minus.setStyleSheet(btn_style)
        self._minus.clicked.connect(self._zoom_out)

        self._lbl = QLabel("100%")
        self._lbl.setFixedWidth(44)
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl.setStyleSheet(
            f"color: {v['TOGGLE_TEXT']}; font-size: 12px; font-weight: 600; "
            f"background: transparent;"
        )
        self._lbl.setToolTip("Current zoom level\nCtrl+0 to reset")

        self._plus = QPushButton("+")
        self._plus.setFixedSize(28, 28)
        self._plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._plus.setToolTip("Zoom in  (Ctrl++)")
        self._plus.setStyleSheet(btn_style)
        self._plus.clicked.connect(self._zoom_in)

        layout.addWidget(self._minus)
        layout.addWidget(self._lbl)
        layout.addWidget(self._plus)

        self.setFixedHeight(34)
        self._refresh_label()

    def _zoom_in(self):
        self._call_zoom(+1)

    def _zoom_out(self):
        self._call_zoom(-1)

    def _call_zoom(self, direction):
        """
        Delegate to the parent BaseWindow if available,
        otherwise manipulate the app font directly.
        """
        parent_win = self.window()
        if parent_win and hasattr(parent_win, "_zoom"):
            parent_win._zoom(direction)
        else:
            from ui.base_window import _do_zoom
            _do_zoom(direction)
        self._refresh_label()

    def _refresh_label(self):
        from ui.base_window import _FONT_SCALE
        pct = round(_FONT_SCALE * 100)
        self._lbl.setText(f"{pct}%")


# ── Backward-compat alias ────────────────────────────────────────────────────
# Old code does: from ui.theme_toggle import ThemeToggleButton
# That still works — it just creates a ZoomWidget now.

class ThemeToggleButton(ZoomWidget):
    """Backward-compatible alias for ZoomWidget."""
    pass
