"""
ui/theme.py  —  Merchant Retail POS
Dark-only theme. Improved contrast + visual differentiation per role.
Zoom level is handled in base_window.py via Ctrl+±/0 and the ZoomWidget.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont


# ── Single dark palette ────────────────────────────────────────────────────────

DARK = {
    # Backgrounds — clearly layered so panels stand out
    "BG_BASE":        "#07111f",   # deepest background
    "BG_SURFACE":     "#0f1f30",   # card / panel surface
    "BG_ELEVATED":    "#172840",   # raised elements (inputs, rows)
    "BG_OVERLAY":     "#1e3350",   # hover state / overlay
    "BG_TOPBAR":      "#0a1929",   # topbar (used as fallback)
    "BG_INPUT":       "#0d1e2e",   # input fields

    # Borders — visible but not heavy
    "BORDER":         "#1e3a5f",
    "BORDER_STRONG":  "#2d5282",
    "BORDER_FOCUS":   "#f59e0b",   # amber focus ring

    # Text — high-contrast hierarchy
    "TEXT_PRIMARY":   "#f0f6ff",   # near-white for body text
    "TEXT_SECONDARY": "#94aac4",   # supporting text
    "TEXT_MUTED":     "#5a7a9a",   # labels, hints
    "TEXT_FAINT":     "#2d4f6b",   # disabled / placeholder
    "TEXT_TOPBAR":    "#f0f6ff",

    # Accent — amber (consistent across roles; topbars use role colours)
    "ACCENT":         "#f59e0b",
    "ACCENT_HOVER":   "#fbbf24",
    "ACCENT_PRESS":   "#d97706",
    "ACCENT_SUBTLE":  "#f59e0b1a",
    "ACCENT_TEXT":    "#0a0400",   # dark text on amber bg

    # Semantic colours
    "GREEN":          "#10d98a",
    "GREEN_BG":       "#10d98a1a",
    "GREEN_TEXT":     "#6ee7b7",
    "RED":            "#f56565",
    "RED_BG":         "#f565651a",
    "RED_TEXT":       "#fca5a5",
    "BLUE":           "#4da3ff",
    "BLUE_BG":        "#4da3ff1a",
    "BLUE_TEXT":      "#93c5fd",
    "PURPLE":         "#c084fc",
    "PURPLE_BG":      "#c084fc1a",
    "PURPLE_TEXT":    "#e9d5ff",
    "ORANGE":         "#fb923c",
    "ORANGE_BG":      "#fb923c1a",

    # Table rows
    "ROW_ALT":        "#0f1f30",
    "ROW_HOVER":      "#172840",
    "ROW_SEL":        "#f59e0b22",
    "ROW_SEL_TEXT":   "#fbbf24",

    # Scrollbars
    "SCROLL_BG":      "#07111f",
    "SCROLL_HANDLE":  "#2d5282",

    # Toggle widget (zoom display)
    "TOGGLE_BG":      "#172840",
    "TOGGLE_BORDER":  "#2d5282",
    "TOGGLE_TEXT":    "#94aac4",
}

# Role topbar colours — visually distinguish who is logged in
ROLE_TOPBAR = {
    "cashier":    "#0a2540",   # deep blue
    "supervisor": "#1a1f0a",   # dark olive/green
    "manager":    "#1a0a20",   # deep purple
    "default":    "#0a1929",
}

ROLE_ACCENT = {
    "cashier":    "#3b82f6",   # blue
    "supervisor": "#22c55e",   # green
    "manager":    "#a855f7",   # purple
    "default":    "#f59e0b",
}


def _build_qss(v):
    return f"""
QMainWindow, QDialog {{
    background-color: {v['BG_BASE']};
    color: {v['TEXT_PRIMARY']};
    font-family: "Segoe UI", "Inter", "Liberation Sans", Arial, sans-serif;
    font-size: 13px;
}}
QWidget {{
    color: {v['TEXT_PRIMARY']};
    font-family: "Segoe UI", "Inter", "Liberation Sans", Arial, sans-serif;
    font-size: 13px;
}}
QFrame {{ background-color: transparent; border: none; }}
QLabel {{ background: transparent; color: {v['TEXT_PRIMARY']}; }}

/* ── Inputs ─────────────────────────────────────────────────────── */
QLineEdit {{
    background-color: {v['BG_INPUT']};
    color: {v['TEXT_PRIMARY']};
    border: 1.5px solid {v['BORDER']};
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 13px;
    selection-background-color: {v['ACCENT']};
    selection-color: {v['ACCENT_TEXT']};
}}
QLineEdit:focus {{ border-color: {v['BORDER_FOCUS']}; background-color: {v['BG_ELEVATED']}; }}
QLineEdit:read-only {{ background-color: {v['BG_BASE']}; color: {v['TEXT_MUTED']}; border-style: dashed; }}
QLineEdit::placeholder {{ color: {v['TEXT_FAINT']}; }}

QTextEdit, QPlainTextEdit {{
    background-color: {v['BG_INPUT']};
    color: {v['TEXT_PRIMARY']};
    border: 1.5px solid {v['BORDER']};
    border-radius: 7px;
    padding: 6px;
}}
QTextEdit:focus, QPlainTextEdit:focus {{ border-color: {v['BORDER_FOCUS']}; }}

QSpinBox, QDoubleSpinBox {{
    background-color: {v['BG_INPUT']};
    color: {v['TEXT_PRIMARY']};
    border: 1.5px solid {v['BORDER']};
    border-radius: 7px;
    padding: 5px 8px;
    min-height: 28px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {v['BORDER_FOCUS']}; }}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: {v['BG_ELEVATED']};
    border: none;
    width: 18px;
    border-radius: 4px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {v['ACCENT']};
}}

/* ── Combo ──────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {v['BG_INPUT']};
    color: {v['TEXT_PRIMARY']};
    border: 1.5px solid {v['BORDER']};
    border-radius: 7px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 30px;
}}
QComboBox:focus {{ border-color: {v['BORDER_FOCUS']}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ width: 10px; height: 10px; }}
QComboBox QAbstractItemView {{
    background-color: {v['BG_SURFACE']};
    color: {v['TEXT_PRIMARY']};
    border: 1.5px solid {v['BORDER_STRONG']};
    border-radius: 7px;
    selection-background-color: {v['ACCENT']};
    selection-color: {v['ACCENT_TEXT']};
    outline: none;
    padding: 4px;
}}

/* ── Buttons ────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {v['BG_ELEVATED']};
    color: {v['TEXT_PRIMARY']};
    border: 1.5px solid {v['BORDER_STRONG']};
    border-radius: 7px;
    padding: 5px 14px;
    font-size: 13px;
    font-weight: 600;
    min-height: 28px;
}}
QPushButton:hover {{
    background-color: {v['BG_OVERLAY']};
    border-color: {v['ACCENT']};
    color: {v['ACCENT']};
}}
QPushButton:pressed {{
    background-color: {v['ACCENT_SUBTLE']};
    border-color: {v['ACCENT_PRESS']};
}}
QPushButton:disabled {{
    color: {v['TEXT_FAINT']};
    border-color: {v['BORDER']};
    background-color: {v['BG_BASE']};
}}

/* ── Tabs ───────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background-color: {v['BG_SURFACE']};
    border-radius: 0 8px 8px 8px;
}}
QTabBar::tab {{
    background-color: {v['BG_BASE']};
    color: {v['TEXT_MUTED']};
    padding: 7px 14px;
    border: 1px solid {v['BORDER']};
    border-bottom: none;
    border-radius: 7px 7px 0 0;
    font-size: 12px;
    font-weight: 600;
    min-width: 80px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background-color: {v['ACCENT']};
    color: {v['ACCENT_TEXT']};
    border-color: {v['ACCENT']};
    font-weight: 700;
}}
QTabBar::tab:hover:!selected {{
    background-color: {v['BG_ELEVATED']};
    color: {v['TEXT_PRIMARY']};
    border-color: {v['BORDER_STRONG']};
}}

/* ── Tables ─────────────────────────────────────────────────────── */
QTableWidget {{
    background-color: transparent;
    color: {v['TEXT_SECONDARY']};
    border: none;
    gridline-color: transparent;
    outline: none;
    font-size: 13px;
}}
QTableWidget::item {{
    padding: 6px 8px;
    border-bottom: 1px solid {v['BG_OVERLAY']};
}}
QTableWidget::item:alternate {{ background-color: {v['ROW_ALT']}; }}
QTableWidget::item:selected {{
    background-color: {v['ROW_SEL']};
    color: {v['ROW_SEL_TEXT']};
}}
QTableWidget::item:hover {{ background-color: {v['ROW_HOVER']}; }}
QHeaderView {{ background-color: transparent; }}
QHeaderView::section {{
    background-color: {v['BG_BASE']};
    color: {v['ACCENT']};
    border: none;
    border-bottom: 2px solid {v['ACCENT']};
    padding: 8px 10px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}}

/* ── Tree ───────────────────────────────────────────────────────── */
QTreeWidget {{
    background-color: {v['BG_SURFACE']};
    color: {v['TEXT_SECONDARY']};
    border: 1.5px solid {v['BORDER']};
    border-radius: 7px;
    outline: none;
}}
QTreeWidget::item {{ padding: 5px 4px; border-bottom: 1px solid {v['BG_OVERLAY']}; }}
QTreeWidget::item:selected {{ background-color: {v['ROW_SEL']}; color: {v['ROW_SEL_TEXT']}; }}
QTreeWidget::item:hover {{ background-color: {v['ROW_HOVER']}; }}
QTreeWidget QHeaderView::section {{
    background-color: {v['BG_BASE']};
    color: {v['ACCENT']};
    border: none;
    border-bottom: 2px solid {v['ACCENT']};
    padding: 6px 8px;
    font-size: 11px;
    font-weight: 700;
}}

/* ── List ───────────────────────────────────────────────────────── */
QListWidget {{
    background-color: {v['BG_SURFACE']};
    color: {v['TEXT_SECONDARY']};
    border: 1.5px solid {v['BORDER']};
    border-radius: 7px;
    outline: none;
}}
QListWidget::item {{ padding: 7px 10px; border-bottom: 1px solid {v['BG_OVERLAY']}; }}
QListWidget::item:selected {{ background-color: {v['ROW_SEL']}; color: {v['ROW_SEL_TEXT']}; }}
QListWidget::item:hover {{ background-color: {v['ROW_HOVER']}; }}

/* ── Scrollbars ─────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {v['SCROLL_BG']};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {v['SCROLL_HANDLE']};
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {v['SCROLL_BG']};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {v['SCROLL_HANDLE']};
    border-radius: 4px;
    min-width: 28px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Checkboxes / Radios ─────────────────────────────────────────── */
QCheckBox {{ color: {v['TEXT_PRIMARY']}; spacing: 9px; font-size: 13px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 2px solid {v['BORDER_STRONG']};
    border-radius: 5px;
    background: {v['BG_INPUT']};
}}
QCheckBox::indicator:checked {{
    background: {v['ACCENT']};
    border-color: {v['ACCENT']};
}}
QCheckBox::indicator:hover {{ border-color: {v['ACCENT_HOVER']}; }}

QRadioButton {{ color: {v['TEXT_PRIMARY']}; spacing: 9px; font-size: 13px; }}
QRadioButton::indicator {{
    width: 18px; height: 18px;
    border: 2px solid {v['BORDER_STRONG']};
    border-radius: 9px;
    background: {v['BG_INPUT']};
}}
QRadioButton::indicator:checked {{
    background: {v['ACCENT']};
    border-color: {v['ACCENT']};
}}

/* ── Tooltips ───────────────────────────────────────────────────── */
QToolTip {{
    background-color: {v['BG_TOPBAR']};
    color: {v['TEXT_TOPBAR']};
    border: 1px solid {v['ACCENT']};
    border-radius: 5px;
    padding: 6px 12px;
    font-size: 12px;
}}

/* ── Dialogs ────────────────────────────────────────────────────── */
QMessageBox {{ background-color: {v['BG_SURFACE']}; }}
QMessageBox QLabel {{ color: {v['TEXT_PRIMARY']}; font-size: 13px; }}
QMessageBox QPushButton {{ min-width: 88px; }}

/* ── Splitter ───────────────────────────────────────────────────── */
QSplitter::handle {{ background-color: {v['BORDER_STRONG']}; border-radius: 2px; }}
QSplitter::handle:horizontal {{ width: 3px; }}
QSplitter::handle:vertical {{ height: 3px; }}

/* ── GroupBox ───────────────────────────────────────────────────── */
QGroupBox {{
    color: {v['TEXT_MUTED']};
    border: 1.5px solid {v['BORDER']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 700;
    font-size: 11px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: {v['ACCENT']};
}}

/* ── Scroll Area ────────────────────────────────────────────────── */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

/* ── Abstract Item View (completer, etc.) ────────────────────────── */
QAbstractItemView {{
    background-color: {v['BG_SURFACE']};
    color: {v['TEXT_PRIMARY']};
    border: 1.5px solid {v['BORDER_STRONG']};
    border-radius: 7px;
    selection-background-color: {v['ACCENT']};
    selection-color: {v['ACCENT_TEXT']};
    outline: none;
    font-size: 13px;
}}
"""


class ThemeManager:
    """
    Dark-only theme manager. Light mode removed per user request.
    Call ThemeManager.instance().apply(app) once at startup.
    """
    _inst = None

    def __init__(self):
        self._callbacks = []

    @classmethod
    def instance(cls):
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    @property
    def is_dark(self):
        return True   # always dark

    @property
    def palette(self):
        return DARK

    def v(self, key):
        return DARK.get(key, "")

    def apply(self, app):
        font = QFont("Segoe UI", 13)
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
        app.setFont(font)
        app.setStyleSheet(_build_qss(DARK))

    def reapply(self):
        """Re-apply QSS to the running app (call after zoom changes)."""
        app = QApplication.instance()
        if app:
            app.setStyleSheet(_build_qss(DARK))

    def on_change(self, callback):
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_change(self, callback):
        self._callbacks = [c for c in self._callbacks if c is not callback]
