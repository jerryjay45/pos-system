# merchant_pos.spec
# ─────────────────────────────────────────────────────────────────────────────
# PyInstaller spec for Merchant Retail POS System
#
# Build on Windows:
#   pyinstaller merchant_pos.spec
#
# Output:
#   dist/MerchantPOS/MerchantPOS.exe   (one-folder mode — recommended)
#
# Distribute the entire dist/MerchantPOS/ folder.
# The storedata/ directory is created automatically on first run
# next to MerchantPOS.exe.
# ─────────────────────────────────────────────────────────────────────────────

import sys
from pathlib import Path

# Root of the source tree (where this .spec lives)
ROOT = Path(SPECPATH)

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    # Entry point
    [str(ROOT / "main.py")],

    pathex=[str(ROOT)],

    # ── Binary dependencies ───────────────────────────────────────────────────
    binaries=[
        # libusb-1.0 — required by python-escpos for USB thermal printer
        # Download libusb-1.0.dll from https://libusb.info and place it next
        # to this .spec file before building, OR install via:
        #   winget install libusb.libusb
        # then find the dll in C:\Windows\System32 or C:\Windows\SysWOW64
        # Uncomment and adjust path once you have the dll:
        # ("C:\\Windows\\System32\\libusb-1.0.dll", "."),
    ],

    # ── Data files (non-Python assets) ───────────────────────────────────────
    datas=[
        # Include the README so it's accessible from the install folder
        (str(ROOT / "README.md"), "."),
        # Include the DBF importer script as a utility
        (str(ROOT / "import_stock_dbf.py"), "."),
    ],

    # ── Hidden imports ────────────────────────────────────────────────────────
    # PyInstaller can't always detect dynamic imports (importlib, lazy loads).
    # List everything that gets imported at runtime.
    hiddenimports=[
        # PyQt6 — core modules
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtPrintSupport",
        "PyQt6.QtSvg",
        "PyQt6.sip",

        # PyQt6 — print support (QPrinter, QPrintDialog)
        "PyQt6.QtPrintSupport",

        # psycopg2 — PostgreSQL sync
        "psycopg2",
        "psycopg2.extras",
        "psycopg2._psycopg",
        "psycopg2.extensions",

        # python-escpos — thermal printer
        "escpos",
        "escpos.printer",
        "escpos.exceptions",
        "escpos.capabilities",
        "usb",
        "usb.core",
        "usb.backend",
        "usb.backend.libusb1",
        "serial",
        "serial.serialutil",
        "serial.serialwin32",

        # Pillow — used by escpos for image printing (logo on receipt)
        "PIL",
        "PIL.Image",
        "PIL.ImageOps",

        # python-barcode — used by label/price tag printing
        "barcode",
        "barcode.writer",
        "barcode.codex",
        "barcode.ean",

        # Standard library modules that PyInstaller sometimes misses
        "sqlite3",
        "pathlib",
        "uuid",
        "hashlib",
        "decimal",
        "struct",
        "json",
        "datetime",
        "importlib",
        "importlib.util",

        # Our own packages
        "config",
        "db",
        "db.models",
        "db.sync",
        "db.connection",
        "core",
        "core.products",
        "core.sales",
        "core.receipts",
        "printing",
        "printing.print_manager",
        "printing.receipt_builder",
        "printing.thermal_printer",
        "printing.normal_printer",
        "printing.formatter",
        "ui",
        "ui.base_window",
        "ui.login_window",
        "ui.main_window",
        "ui.cashier_dashboard",
        "ui.supervisor_dashboard",
        "ui.manager_dashboard",
        "ui.checkout_dialog",
        "ui.cart",
        "ui.dialogs",
        "ui.theme",
        "ui.theme_toggle",
    ],

    # ── PyInstaller hooks ─────────────────────────────────────────────────────
    hookspath=[],
    hooksconfig={
        # Tell the PyQt6 hook to include all required Qt plugins
        "PyQt6": {
            "plugins": [
                "platforms",       # windows.dll — required to show any window
                "platformthemes",  # styling
                "styles",          # QStyle
                "imageformats",    # PNG/JPG support
                "printsupport",    # windowsprintersupport.dll — QPrinter
                "iconengines",     # SVG icons
            ],
        },
    },

    runtime_hooks=[],

    # Modules to explicitly exclude (reduces size)
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "pytest",
        "sphinx",
        "IPython",
        "notebook",
        "PyQt5",
        "PySide2",
        "PySide6",
    ],

    noarchive=False,
    optimize=1,
)

# ── PYZ (Python archive) ──────────────────────────────────────────────────────
pyz = PYZ(a.pure)

# ── EXE ──────────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],

    exclude_binaries=True,   # one-folder mode (not one-file)

    name="MerchantPOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                # compress with UPX if available (optional)
    upx_exclude=[
        # Don't compress Qt DLLs — UPX can break them
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Widgets.dll",
        "Qt6PrintSupport.dll",
        "qwindows.dll",
    ],

    console=False,           # no console window (GUI app)
    # console=True,          # uncomment for debugging — shows console on launch

    # Windows-specific
    disable_windowed_traceback=False,

    # Icon
    icon=str(ROOT / "assets" / "merchant_pos.ico"),
)

# ── COLLECT (one-folder output) ───────────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        "Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll",
        "Qt6PrintSupport.dll", "qwindows.dll",
    ],
    name="MerchantPOS",      # → dist/MerchantPOS/
)
