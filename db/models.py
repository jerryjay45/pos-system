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
            discount_level  INTEGER REFERENCES discount_levels(id) ON DELETE SET NULL,
            discount_level_2 INTEGER REFERENCES discount_levels(id) ON DELETE SET NULL,
            is_case        INTEGER NOT NULL DEFAULT 0,  -- 0 = single, 1 = case
            case_quantity  INTEGER DEFAULT 1,
            gct_applicable INTEGER NOT NULL DEFAULT 1   -- 1 = yes, 0 = exempt
        )
    """)

    # Migration: add discount_level_2 if upgrading from old schema
    existing_prod_cols = {r[1] for r in cursor.execute(
        "PRAGMA table_info(products)"
    ).fetchall()}
    if "discount_level_2" not in existing_prod_cols:
        cursor.execute(
            "ALTER TABLE products ADD COLUMN "
            "discount_level_2 INTEGER REFERENCES discount_levels(id) ON DELETE SET NULL"
        )

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
            id                   INTEGER PRIMARY KEY DEFAULT 1,
            business_name        TEXT,
            address              TEXT,
            phone                TEXT,
            tax_percent          REAL    NOT NULL DEFAULT 16.5,
            receipt_footer       TEXT    DEFAULT 'Thank you for your purchase!',
            case_profit_percent  REAL    NOT NULL DEFAULT 14.0,
            -- Printer settings
            printer_type         TEXT    NOT NULL DEFAULT 'auto',
            thermal_connection   TEXT    NOT NULL DEFAULT 'usb',
            thermal_port         TEXT    NOT NULL DEFAULT '',
            thermal_vendor_id    INTEGER          DEFAULT 0,
            thermal_product_id   INTEGER          DEFAULT 0,
            paper_size           TEXT    NOT NULL DEFAULT 'A4',
            normal_printer_name  TEXT             DEFAULT '',
            receipt_layout       TEXT    NOT NULL DEFAULT 'gct_column'
        )
    """)

    # Always ensure one row exists
    cursor.execute("""
        INSERT OR IGNORE INTO business_info (id, tax_percent) VALUES (1, 16.5)
    """)

    # ── Migration: add printer/layout columns if upgrading ────────────
    existing_biz_cols = {r[1] for r in cursor.execute(
        "PRAGMA table_info(business_info)"
    ).fetchall()}
    biz_migrations = [
        ("printer_type",        "TEXT NOT NULL DEFAULT 'auto'"),
        ("thermal_connection",  "TEXT NOT NULL DEFAULT 'usb'"),
        ("thermal_port",        "TEXT NOT NULL DEFAULT ''"),
        ("thermal_vendor_id",   "INTEGER DEFAULT 0"),
        ("thermal_product_id",  "INTEGER DEFAULT 0"),
        ("paper_size",          "TEXT NOT NULL DEFAULT 'A4'"),
        ("normal_printer_name", "TEXT DEFAULT ''"),
        ("receipt_layout",      "TEXT NOT NULL DEFAULT 'gct_column'"),
    ]
    for col, definition in biz_migrations:
        if col not in existing_biz_cols:
            cursor.execute(
                f"ALTER TABLE business_info ADD COLUMN {col} {definition}"
            )

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

    # Cashing sessions — one per cashier per trading period, opened by supervisor
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cashing_sessions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            cashier_id        INTEGER,            -- the cashier this session belongs to
            cashier_name      TEXT,               -- snapshot
            opened_by_id      INTEGER NOT NULL,   -- supervisor who opened it
            opened_by_name    TEXT    NOT NULL,   -- snapshot
            closed_by_id      INTEGER,
            closed_by_name    TEXT,               -- snapshot
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

    # ── Migration: add cashier_id / cashier_name if upgrading from old schema ──
    existing_cols = {r[1] for r in cursor.execute(
        "PRAGMA table_info(cashing_sessions)"
    ).fetchall()}
    if "cashier_id" not in existing_cols:
        cursor.execute(
            "ALTER TABLE cashing_sessions ADD COLUMN cashier_id INTEGER"
        )
    if "cashier_name" not in existing_cols:
        cursor.execute(
            "ALTER TABLE cashing_sessions ADD COLUMN cashier_name TEXT"
        )

    # Transactions — one per checkout
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id        INTEGER NOT NULL REFERENCES sessions(id),
            cashier_id        INTEGER NOT NULL,
            cashier_name      TEXT    NOT NULL,
            date              TEXT    NOT NULL,
            time              TEXT    NOT NULL,
            subtotal          REAL    NOT NULL DEFAULT 0.0,
            tax_amount        REAL    NOT NULL DEFAULT 0.0,
            discount_total    REAL    NOT NULL DEFAULT 0.0,
            total             REAL    NOT NULL DEFAULT 0.0,
            cash_tendered     REAL    NOT NULL DEFAULT 0.0,
            change_given      REAL    NOT NULL DEFAULT 0.0,
            status            TEXT    NOT NULL DEFAULT 'completed'
                              CHECK(status IN ('completed','voided','refunded')),
            void_reason       TEXT    DEFAULT ''
        )
    """)

    # ── Migration: add cash_tendered / change_given / void_reason / discount_total ──
    existing_tx_cols = {r[1] for r in cursor.execute(
        "PRAGMA table_info(transactions)"
    ).fetchall()}
    tx_migrations = [
        ("cash_tendered",  "REAL NOT NULL DEFAULT 0.0"),
        ("change_given",   "REAL NOT NULL DEFAULT 0.0"),
        ("void_reason",    "TEXT DEFAULT ''"),
        ("discount_total", "REAL NOT NULL DEFAULT 0.0"),
    ]
    for col, definition in tx_migrations:
        if col not in existing_tx_cols:
            cursor.execute(
                f"ALTER TABLE transactions ADD COLUMN {col} {definition}"
            )

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


# ----------------------------------------------------------------
# SELLING PRICE RECALCULATION
# ----------------------------------------------------------------

def recalculate_selling_prices(conn=None, product_ids=None, group_id=None, all_products=False):
    """
    Recalculate selling_price for products and cascade to linked cases.

    Rules:
      - Single with group:    selling_price = cost * (1 + group.profit_percent / 100)
      - Single no group:      selling_price = cost  (sell at cost, no markup)
      - Case:                 case_cost = alias_single.cost * case_quantity
                              selling_price = case_cost * (1 + business.case_profit_percent / 100)

    Pass one of:
      product_ids  — list of specific product IDs to recalculate (singles; cascades to linked cases)
      group_id     — recalculate all singles in this group (then cascade)
      all_products — True to recalculate everything
    """
    close_conn = conn is None
    if conn is None:
        conn = get_products_conn()
    cursor = conn.cursor()

    # Check if cost/selling_price columns exist — if not, fall back to price column
    existing_cols = {r[1] for r in cursor.execute(
        "PRAGMA table_info(products)"
    ).fetchall()}
    has_cost = "cost" in existing_cols and "selling_price" in existing_cols
    if not has_cost:
        # Schema not yet migrated — nothing to recalculate
        if close_conn:
            conn.close()
        return

    # Get case profit % from business.db
    bconn = get_business_conn()
    row   = bconn.execute(
        "SELECT case_profit_percent FROM business_info WHERE id=1"
    ).fetchone()
    bconn.close()
    case_profit_pct = row[0] if row else 14.0

    # Build query for singles to recalculate
    if all_products:
        cursor.execute(
            "SELECT id, cost, group_id, alias_id FROM products WHERE is_case = 0"
        )
    elif group_id is not None:
        cursor.execute(
            "SELECT id, cost, group_id, alias_id FROM products WHERE is_case = 0 AND group_id = ?",
            (group_id,)
        )
    elif product_ids:
        placeholders = ",".join("?" * len(product_ids))
        cursor.execute(
            f"SELECT id, cost, group_id, alias_id FROM products "
            f"WHERE is_case = 0 AND id IN ({placeholders})",
            product_ids
        )
    else:
        if close_conn:
            conn.close()
        return

    singles = cursor.fetchall()
    affected_alias_ids = set()

    for pid, cost, grp_id, alias_id in singles:
        if grp_id:
            grp_row = cursor.execute(
                "SELECT profit_percent FROM product_groups WHERE id = ?", (grp_id,)
            ).fetchone()
            profit_pct    = grp_row[0] if grp_row else 0.0
            selling_price = round(cost * (1 + profit_pct / 100), 2)
        else:
            selling_price = cost  # standalone no-group: sell at cost

        cursor.execute(
            "UPDATE products SET selling_price = ? WHERE id = ?", (selling_price, pid)
        )
        if alias_id:
            affected_alias_ids.add(alias_id)

    # Cascade to cases that share an affected alias
    for alias_id in affected_alias_ids:
        single_row = cursor.execute(
            "SELECT cost FROM products WHERE alias_id = ? AND is_case = 0 LIMIT 1",
            (alias_id,)
        ).fetchone()
        if not single_row:
            continue
        single_cost = single_row[0]

        cases = cursor.execute(
            "SELECT id, case_quantity FROM products WHERE alias_id = ? AND is_case = 1",
            (alias_id,)
        ).fetchall()
        for case_id, case_qty in cases:
            case_qty    = case_qty or 1
            case_cost   = round(single_cost * case_qty, 4)
            case_selling = round(case_cost * (1 + case_profit_pct / 100), 2)
            cursor.execute(
                "UPDATE products SET cost = ?, selling_price = ? WHERE id = ?",
                (case_cost, case_selling, case_id)
            )

    conn.commit()
    if close_conn:
        conn.close()


def recalculate_all_cases(case_profit_pct=None):
    """
    Recalculate selling_price for ALL case products.
    Called when case_profit_percent changes in manager dashboard.
    """
    conn   = get_products_conn()
    cursor = conn.cursor()

    # Check schema
    existing_cols = {r[1] for r in cursor.execute(
        "PRAGMA table_info(products)"
    ).fetchall()}
    if "cost" not in existing_cols or "selling_price" not in existing_cols:
        conn.close()
        return

    if case_profit_pct is None:
        bconn = get_business_conn()
        row   = bconn.execute(
            "SELECT case_profit_percent FROM business_info WHERE id=1"
        ).fetchone()
        bconn.close()
        case_profit_pct = row[0] if row else 14.0

    cases = cursor.execute(
        "SELECT id, alias_id, case_quantity FROM products WHERE is_case = 1"
    ).fetchall()

    for case_id, alias_id, case_qty in cases:
        if not alias_id:
            continue
        single_row = cursor.execute(
            "SELECT cost FROM products WHERE alias_id = ? AND is_case = 0 LIMIT 1",
            (alias_id,)
        ).fetchone()
        if not single_row:
            continue
        case_qty     = case_qty or 1
        case_cost    = round(single_row[0] * case_qty, 4)
        case_selling = round(case_cost * (1 + case_profit_pct / 100), 2)
        cursor.execute(
            "UPDATE products SET cost = ?, selling_price = ? WHERE id = ?",
            (case_cost, case_selling, case_id)
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
