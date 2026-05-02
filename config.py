"""
config.py
Central settings for the POS system.
Change your settings here — no need to dig through other files.
"""

import sys
from pathlib import Path

# ----------------------------------------------------------------
# APPLICATION INFO
# ----------------------------------------------------------------

APP_NAME    = "Merchant POS System"
APP_VERSION = "1.0.0"

# ----------------------------------------------------------------
# DATABASE — LOCAL (SQLite) — 4 separate databases
# ----------------------------------------------------------------

# PyInstaller freezes the app into a single exe or folder.
# When frozen, __file__ points inside the temp extraction dir —
# we want storedata/ to sit next to the .exe, not inside it.
# sys.frozen is set by PyInstaller at runtime.
if getattr(sys, "frozen", False):
    # Running as a PyInstaller bundle
    # sys.executable = path to the .exe file
    BASE_DIR = Path(sys.executable).parent.resolve()
else:
    # Running from source
    BASE_DIR = Path(__file__).parent.resolve()

DATA_DIR = BASE_DIR / "storedata"
DATA_DIR.mkdir(exist_ok=True)

# Each module has its own database file
PRODUCTS_DB     = DATA_DIR / "products.db"
USERS_DB        = DATA_DIR / "users.db"
BUSINESS_DB     = DATA_DIR / "business.db"
TRANSACTIONS_DB = DATA_DIR / "transactions.db"

# ----------------------------------------------------------------
# DATABASE — EXTERNAL (PostgreSQL)
# ----------------------------------------------------------------

USE_POSTGRES = False
#USE_POSTGRES = True

POSTGRES_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "pos_db",
    "user":     "pos_user",
    "password": "changeme",
}

# ----------------------------------------------------------------
# RECEIPT SETTINGS
# ----------------------------------------------------------------

RECEIPT_PRINTER_TYPE = "thermal"
THERMAL_PRINTER_NAME = ""
RECEIPT_COPIES = 1

# ----------------------------------------------------------------
# LABEL SETTINGS
# ----------------------------------------------------------------

LABEL_WIDTH_MM  = 50
LABEL_HEIGHT_MM = 30

# ----------------------------------------------------------------
# UI SETTINGS
# ----------------------------------------------------------------

WINDOW_WIDTH  = 1024
WINDOW_HEIGHT = 768
CHECKOUT_FONT_SIZE = 14

# ----------------------------------------------------------------
# TAX SETTINGS
# ----------------------------------------------------------------

DEFAULT_GCT_RATE = 16.5   # Jamaica standard GCT — manager can change
