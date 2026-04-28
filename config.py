"""
config.py
Central settings for the POS system.
Change your settings here — no need to dig through other files.
"""

from pathlib import Path

# ----------------------------------------------------------------
# APPLICATION INFO
# ----------------------------------------------------------------

APP_NAME    = "POS System"
APP_VERSION = "1.0.0"

# ----------------------------------------------------------------
# DATABASE — LOCAL (SQLite)
# ----------------------------------------------------------------

DATA_DIR = Path.home() / "pos-data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "sales.db"

# ----------------------------------------------------------------
# DATABASE — EXTERNAL (PostgreSQL)
# Set USE_POSTGRES to True and fill in your server details
# to enable syncing to an external PostgreSQL database.
# Leave USE_POSTGRES as False to run in standalone/offline mode.
# ----------------------------------------------------------------

USE_POSTGRES = False

POSTGRES_CONFIG = {
    "host":     "localhost",   # your PostgreSQL server address
    "port":     5432,          # default PostgreSQL port
    "database": "pos_db",      # your database name on the server
    "user":     "pos_user",    # your PostgreSQL username
    "password": "changeme",    # your PostgreSQL password
}

# ----------------------------------------------------------------
# RECEIPT SETTINGS
# ----------------------------------------------------------------

# Printer types: "thermal" or "normal"
RECEIPT_PRINTER_TYPE = "thermal"

# For thermal printers — the printer name as shown in your OS
THERMAL_PRINTER_NAME = ""

# Number of receipt copies to print by default
RECEIPT_COPIES = 1

# ----------------------------------------------------------------
# LABEL SETTINGS
# ----------------------------------------------------------------

# Label size in millimetres (width x height)
LABEL_WIDTH_MM  = 50
LABEL_HEIGHT_MM = 30

# ----------------------------------------------------------------
# UI SETTINGS
# ----------------------------------------------------------------

# Main window size on startup
WINDOW_WIDTH  = 1024
WINDOW_HEIGHT = 768

# Font size for the POS checkout screen
CHECKOUT_FONT_SIZE = 14

# ----------------------------------------------------------------
# TAX SETTINGS
# ----------------------------------------------------------------

# Default GCT rate applied on first run only.
# After that, the manager can change it from the settings screen
# and it will be saved in the database (business_info table).
DEFAULT_GCT_RATE = 16.5   # Jamaica standard GCT rate
