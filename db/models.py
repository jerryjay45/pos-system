"""
db/models.py
Creates all database tables for the POS system.
Run this once when the app starts to set up the database.
"""

import sqlite3
import sys
from pathlib import Path

# Add the project root to the path so we can import config.py
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_PATH


def get_connection():
    """Open and return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")  # enforce FK relationships
    return conn


def create_tables():
    """Create all tables if they don't already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # ----------------------------------------------------------------
    # PRODUCTS MODULE
    # ----------------------------------------------------------------

    # Alias — group identifier for products that share a description
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aliases (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            alias_name  TEXT    NOT NULL UNIQUE,
            description TEXT
        )
    """)

    # Discount levels — tiered discounts based on quantity purchased
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS discount_levels (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            level_name       TEXT    NOT NULL,
            min_quantity     INTEGER NOT NULL DEFAULT 1,
            discount_percent REAL    NOT NULL DEFAULT 0.0
        )
    """)

    # Products — core product table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode        TEXT    NOT NULL UNIQUE,
            brand          TEXT,
            name           TEXT    NOT NULL,
            price          REAL    NOT NULL DEFAULT 0.0,
            alias_id       INTEGER REFERENCES aliases(id) ON UPDATE CASCADE ON DELETE SET NULL,
            discount_level INTEGER REFERENCES discount_levels(id) ON DELETE SET NULL,
            case_quantity  INTEGER DEFAULT 1,
            stock_enabled  INTEGER NOT NULL DEFAULT 1  -- 1 = active, 0 = hidden
        )
    """)

    # ----------------------------------------------------------------
    # USERS MODULE
    # ----------------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            full_name     TEXT    NOT NULL,
            role          TEXT    NOT NULL CHECK(role IN ('cashier', 'supervisor', 'manager')),
            is_active     INTEGER NOT NULL DEFAULT 1  -- 1 = active, 0 = deactivated
        )
    """)

    # ----------------------------------------------------------------
    # CHECKOUT MODULE
    # ----------------------------------------------------------------

    # Sessions — one per cashier login shift
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cashier_id  INTEGER NOT NULL REFERENCES users(id),
            started_at  TEXT    NOT NULL,
            ended_at    TEXT,
            total_sales REAL    NOT NULL DEFAULT 0.0
        )
    """)

    # Transactions — one per checkout
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL REFERENCES sessions(id),
            cashier_id  INTEGER NOT NULL REFERENCES users(id),
            date        TEXT    NOT NULL,
            time        TEXT    NOT NULL,
            subtotal    REAL    NOT NULL DEFAULT 0.0,
            tax_amount  REAL    NOT NULL DEFAULT 0.0,
            total       REAL    NOT NULL DEFAULT 0.0,
            status      TEXT    NOT NULL DEFAULT 'completed'
                        CHECK(status IN ('completed', 'voided', 'refunded'))
        )
    """)

    # Transaction items — one row per product in a transaction
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_items (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id   INTEGER NOT NULL REFERENCES transactions(id),
            product_id       INTEGER NOT NULL REFERENCES products(id),
            quantity         INTEGER NOT NULL DEFAULT 1,
            unit_price       REAL    NOT NULL,
            discount_applied REAL    NOT NULL DEFAULT 0.0,
            line_total       REAL    NOT NULL
        )
    """)

    # ----------------------------------------------------------------
    # BUSINESS SETTINGS
    # ----------------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_info (
            id              INTEGER PRIMARY KEY DEFAULT 1,
            business_name   TEXT,
            address         TEXT,
            phone           TEXT,
            tax_percent     REAL    NOT NULL DEFAULT 0.0,
            receipt_footer  TEXT    DEFAULT 'Thank you for your purchase!'
        )
    """)

    # Insert default business info row if it doesn't exist
    cursor.execute("""
        INSERT OR IGNORE INTO business_info (id, tax_percent) VALUES (1, 16.5)
    """)

    # ----------------------------------------------------------------
    # QUICK KEYS — F1-F8 product shortcuts assigned by manager
    # ----------------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quick_keys (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key_number  INTEGER NOT NULL UNIQUE CHECK(key_number BETWEEN 1 AND 8),
            product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print(f"Database ready at: {DB_PATH}")


if __name__ == "__main__":
    create_tables()
