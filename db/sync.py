"""
db/sync.py
PostgreSQL bidirectional sync for Merchant Retail POS.

Architecture
------------
- SQLite is always the primary/live database. PostgreSQL is the remote replica.
- PUSH: writes local SQLite changes up to PostgreSQL.
- PULL: pulls remote changes (e.g. from another terminal) back to SQLite.
- Each synced table has a `synced_at` TEXT column (ISO-8601) and a
  `sync_id` TEXT column (UUID) used as the stable cross-DB key.
- A local `sync_log` table in transactions.db records every sync event.

Usage (from manager dashboard or CLI):
    from db.sync import SyncManager
    sm = SyncManager()
    ok, msg = sm.test_connection()
    ok, msg = sm.push_all()
    ok, msg = sm.pull_all()
    ok, msg = sm.sync()       # push then pull
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


# ── Import local DB helpers ────────────────────────────────────────────────────

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    USE_POSTGRES, POSTGRES_CONFIG,
    PRODUCTS_DB, USERS_DB, BUSINESS_DB, TRANSACTIONS_DB,
)


# ── Tables that participate in sync ───────────────────────────────────────────

SYNC_TABLES = {
    "products":       PRODUCTS_DB,
    "aliases":        PRODUCTS_DB,
    "product_groups": PRODUCTS_DB,
    "discount_levels":PRODUCTS_DB,
    "quick_keys":     PRODUCTS_DB,
    "users":          USERS_DB,
    "business_info":  BUSINESS_DB,
    "transactions":   TRANSACTIONS_DB,
    "transaction_items": TRANSACTIONS_DB,
    "cashing_sessions":  TRANSACTIONS_DB,
}

# Read-only on pull (we never overwrite local transaction history from remote)
PULL_SKIP = {"transactions", "transaction_items", "cashing_sessions"}


# ── Sync log ──────────────────────────────────────────────────────────────────

def _ensure_sync_log():
    """Create sync_log table in transactions.db if it doesn't exist."""
    conn = sqlite3.connect(TRANSACTIONS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event      TEXT    NOT NULL,   -- 'push' | 'pull' | 'error' | 'test'
            table_name TEXT,
            rows_affected INTEGER DEFAULT 0,
            message    TEXT,
            created_at TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _log(event, table_name=None, rows=0, message=None):
    try:
        _ensure_sync_log()
        conn = sqlite3.connect(TRANSACTIONS_DB)
        conn.execute(
            "INSERT INTO sync_log (event, table_name, rows_affected, message, created_at)"
            " VALUES (?,?,?,?,?)",
            (event, table_name, rows, message,
             datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


# ── PostgreSQL connection ──────────────────────────────────────────────────────

def _pg_connect():
    """
    Return a psycopg2 connection or raise ImportError / Exception.
    """
    try:
        import psycopg2
    except ImportError:
        raise ImportError(
            "psycopg2 is not installed.\n"
            "Run: pip install psycopg2-binary"
        )
    cfg = POSTGRES_CONFIG
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        dbname=cfg["database"],
        user=cfg["user"],
        password=cfg["password"],
        connect_timeout=10,
    )
    conn.autocommit = False
    return conn


# ── Schema mirroring ──────────────────────────────────────────────────────────

_PG_TYPE_MAP = {
    "INTEGER": "BIGINT",
    "REAL":    "DOUBLE PRECISION",
    "TEXT":    "TEXT",
    "BLOB":    "BYTEA",
    "NUMERIC": "NUMERIC",
}

def _sqlite_to_pg_type(sqlite_type):
    for k, v in _PG_TYPE_MAP.items():
        if k in sqlite_type.upper():
            return v
    return "TEXT"


def _mirror_schema(pg_conn, table, sqlite_db_path):
    """
    Create the table in PostgreSQL if it doesn't exist, mirroring
    the SQLite schema. Adds sync_id + synced_at helper columns.
    """
    sc = sqlite3.connect(sqlite_db_path)
    cols = sc.execute(f"PRAGMA table_info({table})").fetchall()
    sc.close()

    if not cols:
        return  # Table doesn't exist in SQLite yet

    col_defs = []
    for cid, name, ctype, notnull, default, pk in cols:
        pg_type = _sqlite_to_pg_type(ctype or "TEXT")
        if pk:
            if pg_type == "BIGINT":
                col_defs.append(f'"{name}" BIGSERIAL PRIMARY KEY')
            else:
                col_defs.append(f'"{name}" {pg_type} PRIMARY KEY')
        else:
            nn  = "NOT NULL" if notnull else ""
            dfl = f"DEFAULT {default}" if default is not None else ""
            col_defs.append(f'"{name}" {pg_type} {nn} {dfl}'.strip())

    # Add sync helper columns if not already in the list
    existing_names = {c[1] for c in cols}
    if "sync_id" not in existing_names:
        col_defs.append('"sync_id" TEXT UNIQUE')
    if "synced_at" not in existing_names:
        col_defs.append('"synced_at" TEXT')

    ddl = f'CREATE TABLE IF NOT EXISTS "{table}" (\n  ' + ",\n  ".join(col_defs) + "\n);"

    cur = pg_conn.cursor()
    cur.execute(ddl)
    pg_conn.commit()


def ensure_remote_schema(pg_conn=None):
    """
    Mirror all SYNC_TABLES schemas to PostgreSQL.
    Returns (True, "OK") or (False, error_message).
    """
    close = pg_conn is None
    try:
        if pg_conn is None:
            pg_conn = _pg_connect()
        for table, db_path in SYNC_TABLES.items():
            _mirror_schema(pg_conn, table, db_path)
        if close:
            pg_conn.commit()
            pg_conn.close()
        return True, "Schema mirrored successfully."
    except Exception as e:
        if close and pg_conn:
            try: pg_conn.close()
            except Exception: pass
        return False, str(e)


# ── Push (SQLite → PostgreSQL) ────────────────────────────────────────────────

def _push_table(pg_conn, table, sqlite_db_path):
    """
    Upsert all rows from SQLite table into PostgreSQL.
    Returns number of rows pushed.
    """
    sc   = sqlite3.connect(sqlite_db_path)
    sc.row_factory = sqlite3.Row
    rows = sc.execute(f"SELECT * FROM {table}").fetchall()
    sc.close()

    if not rows:
        return 0

    import psycopg2.extras

    cur     = pg_conn.cursor()
    count   = 0
    columns = list(rows[0].keys())

    # Ensure sync_id column exists in PG
    try:
        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS sync_id TEXT UNIQUE')
        cur.execute(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS synced_at TEXT')
        pg_conn.commit()
    except Exception:
        pg_conn.rollback()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for row in rows:
        vals = dict(row)
        # Assign a stable sync_id if row doesn't have one (use table+id)
        sync_id = f"{table}_{vals.get('id', uuid.uuid4().hex)}"
        vals["sync_id"]  = sync_id
        vals["synced_at"] = now

        all_cols  = list(vals.keys())
        pg_cols   = [f'"{c}"' for c in all_cols]
        pg_vals   = list(vals.values())
        placeholders = ", ".join(["%s"] * len(all_cols))

        # Build ON CONFLICT upsert
        update_set = ", ".join(
            f'"{c}" = EXCLUDED."{c}"'
            for c in all_cols if c not in ("id", "sync_id")
        )

        sql = (
            f'INSERT INTO "{table}" ({", ".join(pg_cols)}) '
            f'VALUES ({placeholders}) '
            f'ON CONFLICT (sync_id) DO UPDATE SET {update_set}'
        )

        try:
            cur.execute(sql, pg_vals)
            count += 1
        except Exception as e:
            pg_conn.rollback()
            raise RuntimeError(f"Push failed on {table} row {vals.get('id')}: {e}")

    pg_conn.commit()
    return count


# ── Pull (PostgreSQL → SQLite) ────────────────────────────────────────────────

def _pull_table(pg_conn, table, sqlite_db_path):
    """
    Pull rows from PostgreSQL that are newer than the latest local synced_at.
    Returns number of rows pulled.
    """
    if table in PULL_SKIP:
        return 0   # Never overwrite local transaction history

    # Get last local sync time for this table
    sc = sqlite3.connect(sqlite_db_path)
    local_cols = {r[1] for r in sc.execute(f"PRAGMA table_info({table})").fetchall()}

    last_sync = "1970-01-01T00:00:00Z"
    if "synced_at" in local_cols:
        row = sc.execute(f"SELECT MAX(synced_at) FROM {table}").fetchone()
        if row and row[0]:
            last_sync = row[0]

    import psycopg2.extras
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        cur.execute(
            f'SELECT * FROM "{table}" WHERE synced_at > %s ORDER BY synced_at ASC',
            (last_sync,)
        )
    except Exception:
        return 0   # Table may not exist on remote yet

    remote_rows = cur.fetchall()
    if not remote_rows:
        sc.close()
        return 0

    count = 0
    for row in remote_rows:
        row_dict = dict(row)
        # Strip PG-only helper columns not in SQLite
        row_dict = {k: v for k, v in row_dict.items() if k in local_cols}

        cols  = list(row_dict.keys())
        vals  = list(row_dict.values())
        placeholders = ", ".join(["?"] * len(cols))
        update_set   = ", ".join(
            f'"{c}" = ?' for c in cols if c != "id"
        )
        update_vals  = [row_dict[c] for c in cols if c != "id"]

        sql = (
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {update_set}"
        )
        try:
            sc.execute(sql, vals + update_vals)
            count += 1
        except Exception:
            pass   # Skip rows with constraint violations

    sc.commit()
    sc.close()
    return count


# ── Public API ────────────────────────────────────────────────────────────────

class SyncManager:
    """
    Single entry point for all sync operations.

    Example:
        sm = SyncManager()
        ok, msg = sm.test_connection()
        ok, msg = sm.push_all()
        ok, msg = sm.pull_all()
        ok, msg = sm.sync()
    """

    def test_connection(self):
        """Test the PostgreSQL connection. Returns (True, info) or (False, error)."""
        if not USE_POSTGRES:
            return False, "PostgreSQL sync is disabled (USE_POSTGRES = False in config.py)."
        try:
            pg = _pg_connect()
            cur = pg.cursor()
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            pg.close()
            _log("test", message=f"Connection OK — {version[:60]}")
            return True, f"Connected.\n{version[:80]}"
        except Exception as e:
            _log("error", message=f"Connection test failed: {e}")
            return False, str(e)

    def ensure_schema(self):
        """Mirror SQLite schema to PostgreSQL. Safe to run multiple times."""
        if not USE_POSTGRES:
            return False, "PostgreSQL sync is disabled."
        try:
            pg = _pg_connect()
            ok, msg = ensure_remote_schema(pg)
            pg.close()
            return ok, msg
        except Exception as e:
            return False, str(e)

    def push_all(self, progress_callback=None):
        """
        Push all local SQLite data to PostgreSQL.
        progress_callback(table_name, rows_pushed) called for each table.
        Returns (True, summary) or (False, error).
        """
        if not USE_POSTGRES:
            return False, "PostgreSQL sync is disabled."
        try:
            pg = _pg_connect()
            ensure_remote_schema(pg)
            total = 0
            results = []
            for table, db_path in SYNC_TABLES.items():
                try:
                    n = _push_table(pg, table, db_path)
                    total += n
                    results.append(f"  {table}: {n} rows")
                    _log("push", table_name=table, rows=n)
                    if progress_callback:
                        progress_callback(table, n)
                except Exception as e:
                    results.append(f"  {table}: ERROR — {e}")
                    _log("error", table_name=table, message=str(e))
            pg.close()
            summary = f"Push complete. {total} rows total.\n" + "\n".join(results)
            return True, summary
        except Exception as e:
            _log("error", message=f"Push failed: {e}")
            return False, str(e)

    def pull_all(self, progress_callback=None):
        """
        Pull remote PostgreSQL changes into SQLite.
        Transaction tables are never overwritten.
        Returns (True, summary) or (False, error).
        """
        if not USE_POSTGRES:
            return False, "PostgreSQL sync is disabled."
        try:
            pg = _pg_connect()
            total = 0
            results = []
            for table, db_path in SYNC_TABLES.items():
                if table in PULL_SKIP:
                    results.append(f"  {table}: skipped (local-only)")
                    continue
                try:
                    n = _pull_table(pg, table, db_path)
                    total += n
                    results.append(f"  {table}: {n} rows")
                    _log("pull", table_name=table, rows=n)
                    if progress_callback:
                        progress_callback(table, n)
                except Exception as e:
                    results.append(f"  {table}: ERROR — {e}")
                    _log("error", table_name=table, message=str(e))
            pg.close()
            summary = f"Pull complete. {total} rows synced.\n" + "\n".join(results)
            return True, summary
        except Exception as e:
            _log("error", message=f"Pull failed: {e}")
            return False, str(e)

    def sync(self, progress_callback=None):
        """Push then pull. Returns (True, summary) or (False, error)."""
        ok1, msg1 = self.push_all(progress_callback)
        if not ok1:
            return False, f"Push failed: {msg1}"
        ok2, msg2 = self.pull_all(progress_callback)
        if not ok2:
            return False, f"Pull failed: {msg2}"
        return True, f"--- PUSH ---\n{msg1}\n\n--- PULL ---\n{msg2}"

    def get_log(self, limit=50):
        """Return recent sync log entries as list of dicts."""
        try:
            _ensure_sync_log()
            conn = sqlite3.connect(TRANSACTIONS_DB)
            rows = conn.execute(
                "SELECT id, event, table_name, rows_affected, message, created_at"
                " FROM sync_log ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            conn.close()
            return [
                {"id": r[0], "event": r[1], "table": r[2],
                 "rows": r[3], "message": r[4], "time": r[5]}
                for r in rows
            ]
        except Exception:
            return []


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="POS PostgreSQL sync")
    parser.add_argument("action", choices=["test", "schema", "push", "pull", "sync", "log"])
    args = parser.parse_args()

    sm = SyncManager()
    if args.action == "test":
        ok, msg = sm.test_connection()
    elif args.action == "schema":
        ok, msg = sm.ensure_schema()
    elif args.action == "push":
        ok, msg = sm.push_all(lambda t, n: print(f"  pushed {t}: {n}"))
    elif args.action == "pull":
        ok, msg = sm.pull_all(lambda t, n: print(f"  pulled {t}: {n}"))
    elif args.action == "sync":
        ok, msg = sm.sync(lambda t, n: print(f"  synced {t}: {n}"))
    elif args.action == "log":
        entries = sm.get_log()
        for e in entries:
            print(f"[{e['time']}] {e['event']:6} {e['table'] or '':20} rows={e['rows']:4}  {e['message'] or ''}")
        ok, msg = True, f"{len(entries)} log entries."

    print("\n" + ("✓" if ok else "✗"), msg)
