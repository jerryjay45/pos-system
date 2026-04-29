"""
db/models.py
Creates all database tables across 4 separate database files:
  - products.db     — products, aliases, groups, discount levels, quick keys
  - users.db        — users
  - business.db     — business info, settings
  - transactions.db — sessions, cashing sessions, transactions, items

Separation means products/users can be deleted without
breaking transaction history — items store snapshots at time of sale.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PRODUCTS_DB, USERS_DB, BUSINESS_DB, TRANSACTIONS_DB

import sqlite3


# ----------------------------------------------------------------
# CONNECTION HELPERS
# ----------------------------------------------------------------

def get_products_conn():
    conn = sqlite3.connect(PRODUCTS_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_users_conn():
    conn = sqlite3.connect(USERS_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_business_conn():
    conn = sqlite3.connect(BUSINESS_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_transactions_conn():
    conn = sqlite3.connect(TRANSACTIONS_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ----------------------------------------------------------------
# PRODUCTS DATABASE
# ----------------------------------------------------------------

def create_products_tables():
    conn   = get_products_conn()
    cursor = conn.cursor()

    # Product groups — Frozen, Bulk, Canned, Fresh etc.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_groups (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name     TEXT    NOT NULL UNIQUE,
            profit_percent REAL    NOT NULL DEFAULT 0.0
        )
    """)

    # Aliases — shared group identifier for related products
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aliases (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            alias_name  TEXT    NOT NULL UNIQUE,
            description TEXT
        )
    """)

    # Discount levels — tiered discounts by quantity
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS discount_levels (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            level_name       TEXT    NOT NULL,
            min_quantity     INTEGER NOT NULL DEFAULT 1,
            discount_percent REAL    NOT NULL DEFAULT 0.0
        )
    """)

    # Products
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode        TEXT    NOT NULL UNIQUE,
            brand          TEXT,
            name           TEXT    NOT NULL,
            price          REAL    NOT NULL DEFAULT 0.0,
            alias_id       INTEGER REFERENCES aliases(id) ON UPDATE CASCADE ON DELETE SET NULL,
            group_id       INTEGER REFERENCES product_groups(id) ON DELETE SET NULL,
            discount_level INTEGER REFERENCES discount_levels(id) ON DELETE SET NULL,
            is_case        INTEGER NOT NULL DEFAULT 0,  -- 0 = single, 1 = case
            case_quantity  INTEGER DEFAULT 1,
            gct_applicable INTEGER NOT NULL DEFAULT 1   -- 1 = yes, 0 = exempt
        )
    """)

    # Quick keys — F1-F8 shortcuts assigned by manager
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quick_keys (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key_number  INTEGER NOT NULL UNIQUE CHECK(key_number BETWEEN 1 AND 8),
            product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE
        )
    """)

    # Default product groups
    defaults = [
        ("Canned",   25.0), ("Frozen",   25.0), ("Bulk",     25.0),
        ("Fresh",    25.0), ("Bakery",   25.0), ("Beverage", 25.0),
        ("Household",25.0), ("Personal", 25.0),
    ]
    for name, profit in defaults:
        cursor.execute(
            "INSERT OR IGNORE INTO product_groups (group_name, profit_percent) VALUES (?,?)",
            (name, profit)
        )

    conn.commit()
    conn.close()
    print(f"products.db ready at: {PRODUCTS_DB}")


# ----------------------------------------------------------------
# USERS DATABASE
# ----------------------------------------------------------------

def create_users_tables():
    conn   = get_users_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            full_name     TEXT    NOT NULL,
            role          TEXT    NOT NULL CHECK(role IN ('cashier','supervisor','manager')),
            is_active     INTEGER NOT NULL DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()
    print(f"users.db ready at: {USERS_DB}")


# ----------------------------------------------------------------
# BUSINESS DATABASE
# ----------------------------------------------------------------

def create_business_tables():
    conn   = get_business_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_info (
            id                  INTEGER PRIMARY KEY DEFAULT 1,
            business_name       TEXT,
            address             TEXT,
            phone               TEXT,
            tax_percent         REAL    NOT NULL DEFAULT 16.5,
            receipt_footer      TEXT    DEFAULT 'Thank you for your purchase!',
            case_profit_percent REAL    NOT NULL DEFAULT 14.0
        )
    """)

    # Always ensure one row exists
    cursor.execute("""
        INSERT OR IGNORE INTO business_info (id, tax_percent) VALUES (1, 16.5)
    """)

    conn.commit()
    conn.close()
    print(f"business.db ready at: {BUSINESS_DB}")


# ----------------------------------------------------------------
# TRANSACTIONS DATABASE
# ----------------------------------------------------------------

def create_transactions_tables():
    conn   = get_transactions_conn()
    cursor = conn.cursor()

    # Cashier sessions — one per login shift
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            cashier_id        INTEGER NOT NULL,
            cashier_name      TEXT    NOT NULL,  -- snapshot
            started_at        TEXT    NOT NULL,
            ended_at          TEXT,
            total_sales       REAL    NOT NULL DEFAULT 0.0
        )
    """)

    # Cashing sessions — supervisor-defined trading periods
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cashing_sessions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            opened_by_id      INTEGER NOT NULL,
            opened_by_name    TEXT    NOT NULL,  -- snapshot
            closed_by_id      INTEGER,
            closed_by_name    TEXT,              -- snapshot
            opened_at         TEXT    NOT NULL,
            closed_at         TEXT,
            total_sales       REAL    NOT NULL DEFAULT 0.0,
            total_gct         REAL    NOT NULL DEFAULT 0.0,
            total_discount    REAL    NOT NULL DEFAULT 0.0,
            transaction_count INTEGER NOT NULL DEFAULT 0,
            status            TEXT    NOT NULL DEFAULT 'open'
                              CHECK(status IN ('open','closed'))
        )
    """)

    # Transactions — one per checkout
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id        INTEGER NOT NULL REFERENCES sessions(id),
            cashier_id        INTEGER NOT NULL,
            cashier_name      TEXT    NOT NULL,  -- snapshot
            date              TEXT    NOT NULL,
            time              TEXT    NOT NULL,
            subtotal          REAL    NOT NULL DEFAULT 0.0,
            tax_amount        REAL    NOT NULL DEFAULT 0.0,
            total             REAL    NOT NULL DEFAULT 0.0,
            status            TEXT    NOT NULL DEFAULT 'completed'
                              CHECK(status IN ('completed','voided','refunded'))
        )
    """)

    # Transaction items — snapshot of product at time of sale
    # Stored independently — deleting a product won't break history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_items (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id        INTEGER NOT NULL REFERENCES transactions(id),
            product_id            INTEGER,        -- reference only, may be NULL if deleted
            product_name_snapshot TEXT    NOT NULL,  -- snapshot
            barcode_snapshot      TEXT    NOT NULL,  -- snapshot
            unit_price_snapshot   REAL    NOT NULL,  -- snapshot
            quantity              INTEGER NOT NULL DEFAULT 1,
            gct_applicable        INTEGER NOT NULL DEFAULT 1,
            discount_applied      REAL    NOT NULL DEFAULT 0.0,
            line_total            REAL    NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print(f"transactions.db ready at: {TRANSACTIONS_DB}")


# ----------------------------------------------------------------
# CREATE ALL
# ----------------------------------------------------------------

def create_tables():
    """Create all tables across all 4 databases."""
    create_products_tables()
    create_users_tables()
    create_business_tables()
    create_transactions_tables()


if __name__ == "__main__":
    create_tables()
