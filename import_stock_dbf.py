#!/usr/bin/env python3
"""
import_stock_dbf.py
───────────────────
Imports STOCK.DBF (dBase III/IV) into the POS products.db.

Usage:
    python import_stock_dbf.py STOCK.DBF [--db path/to/storedata/products.db]

What it does
────────────
  • Reads every non-deleted record from the DBF file
  • Creates product_groups from the GROUP field
  • Creates discount_levels from the unique QUAN1/PRICEM1 and QUAN2/PRICEM2
    price-break tiers found in the data (converts price → % off selling price)
  • Inserts products, skipping duplicates (by barcode) with a warning
  • Reports totals at the end

Field mapping
─────────────
  DBF CODE        → products.barcode
  DBF DESCRIP     → products.name
  DBF CATEGORY    → products.brand   (e.g. "CANTEEN")
  DBF PRICE       → products.selling_price  (and .price)
  DBF COST        → products.cost
  DBF GCT  T/F    → products.gct_applicable  1/0
  DBF QUANTITY    → products.stock_qty  (added if column missing)
  DBF GROUP       → products.group_id  (FK → product_groups)
  DBF QUAN1+PRICEM1 → products.discount_level   (FK → discount_levels)
  DBF QUAN2+PRICEM2 → products.discount_level_2 (FK → discount_levels)
"""

import argparse
import os
import sqlite3
import struct
import sys
from collections import defaultdict


# ── DBF reader (no external dependencies) ────────────────────────────────────

def read_dbf(path):
    """Parse a dBase III/IV .DBF file; returns (field_list, record_list)."""
    data = open(path, "rb").read()

    num_records = struct.unpack_from("<I", data, 4)[0]
    header_size = struct.unpack_from("<H", data, 8)[0]
    record_size = struct.unpack_from("<H", data, 10)[0]

    fields = []
    offset = 32
    while data[offset] != 0x0D:
        name  = data[offset:offset+11].split(b"\x00")[0].decode("latin-1").strip()
        ftype = chr(data[offset + 11])
        flen  = data[offset + 16]
        fields.append((name, ftype, flen))
        offset += 32

    records = []
    for r in range(num_records):
        ro = header_size + r * record_size
        if data[ro] == ord("*"):        # deleted record
            continue
        pos = ro + 1
        rec = {}
        for name, ftype, flen in fields:
            raw = data[pos:pos+flen].decode("latin-1").strip()
            rec[name] = raw
            pos += flen
        records.append(rec)

    return fields, records


def _float(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _int(s):
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def _bool_dbf(s):
    """DBF logical: 'T'/'Y' → 1, anything else → 0."""
    return 1 if s.upper() in ("T", "Y") else 0


# ── Main importer ─────────────────────────────────────────────────────────────

def import_dbf(dbf_path, db_path):
    print(f"\n{'─'*60}")
    print(f"  Importing:  {dbf_path}")
    print(f"  Into:       {db_path}")
    print(f"{'─'*60}\n")

    # ── 1. Read DBF ──────────────────────────────────────────────────
    fields, records = read_dbf(dbf_path)
    print(f"  DBF records (non-deleted): {len(records)}")

    # ── 2. Open / initialise products.db ────────────────────────────
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur  = conn.cursor()

    # Ensure stock_qty column exists (may not be in older schema)
    existing_cols = {r[1] for r in cur.execute("PRAGMA table_info(products)").fetchall()}
    if "stock_qty" not in existing_cols:
        cur.execute("ALTER TABLE products ADD COLUMN stock_qty REAL NOT NULL DEFAULT 0.0")
        conn.commit()
        print("  Added stock_qty column to products table.")

    # ── 3. Build product groups ──────────────────────────────────────
    group_names = sorted({r["GROUP"] for r in records if r["GROUP"]})
    group_id_map = {}   # group_name → id

    for gname in group_names:
        cur.execute(
            "INSERT OR IGNORE INTO product_groups (group_name, profit_percent) VALUES (?, 0.0)",
            (gname,)
        )
        row = cur.execute(
            "SELECT id FROM product_groups WHERE group_name = ?", (gname,)
        ).fetchone()
        group_id_map[gname] = row[0]

    conn.commit()
    print(f"  Product groups created/found: {len(group_id_map)}  {list(group_id_map.keys())}")

    # ── 4. Build discount levels from QUAN+PRICEM tiers ──────────────
    # Each unique (min_qty, discount_pct) pair becomes one discount_level row.
    # discount_pct is derived: round((selling_price - tier_price) / selling_price * 100, 4)
    # We collect all tier pairs across all records first.

    tier_set = set()   # set of (min_qty_int, discount_pct_rounded)

    for r in records:
        sp = _float(r["PRICE"]) or _float(r["PRICEG"])
        if sp <= 0:
            continue
        for q_field, p_field in [("QUAN1", "PRICEM1"), ("QUAN2", "PRICEM2"), ("QUAN3", "PRICEM3")]:
            qty   = _float(r[q_field])
            price = _float(r[p_field])
            if qty > 0 and 0 < price < sp:
                # Round to 1 dp so floating-point variations in DBF data
                # collapse to a small set of meaningful discount levels
                pct = round((sp - price) / sp * 100, 1)
                if pct > 0:
                    tier_set.add((int(qty), pct))

    # Sort by min_qty for readability
    tiers_sorted = sorted(tier_set)
    disc_id_map  = {}   # (min_qty, pct) → discount_level id

    for min_qty, pct in tiers_sorted:
        level_name = f"Buy {min_qty}+ ({pct:.2f}% off)"
        cur.execute(
            "INSERT OR IGNORE INTO discount_levels (level_name, min_quantity, discount_percent) VALUES (?, ?, ?)",
            (level_name, min_qty, pct)
        )
        row = cur.execute(
            "SELECT id FROM discount_levels WHERE level_name = ?", (level_name,)
        ).fetchone()
        disc_id_map[(min_qty, pct)] = row[0]

    conn.commit()
    print(f"  Discount levels created/found: {len(disc_id_map)}")
    for k, v in disc_id_map.items():
        print(f"    id={v}  min_qty={k[0]}  {k[1]:.4f}%")

    # ── 5. Import products ────────────────────────────────────────────
    inserted = 0
    skipped  = 0
    no_barcode = 0
    errors   = []

    for r in records:
        barcode = r["CODE"].strip()
        if not barcode:
            no_barcode += 1
            continue

        name          = r["DESCRIP"].strip() or "(no name)"
        brand         = r["CATEGORY"].strip() or None
        selling_price = _float(r["PRICE"]) or _float(r["PRICEG"])
        cost          = _float(r["COST"])
        gct           = _bool_dbf(r["GCT"])
        stock_qty     = _float(r["QUANTITY"])
        group_id      = group_id_map.get(r["GROUP"]) if r["GROUP"] else None

        # Resolve discount_level and discount_level_2
        def resolve_tier(q_field, p_field):
            sp = selling_price
            if sp <= 0:
                return None
            qty   = _float(r[q_field])
            price = _float(r[p_field])
            if qty > 0 and 0 < price < sp:
                pct = round((sp - price) / sp * 100, 1)
                return disc_id_map.get((int(qty), pct))
            return None

        disc1 = resolve_tier("QUAN1", "PRICEM1")
        disc2 = resolve_tier("QUAN2", "PRICEM2")
        # Avoid setting disc2 = disc1
        if disc2 == disc1:
            disc2 = None

        try:
            cur.execute("""
                INSERT INTO products
                    (barcode, brand, name, cost, selling_price,
                     gct_applicable, stock_qty, group_id,
                     discount_level, discount_level_2,
                     is_case, case_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
            """, (
                barcode, brand, name, cost, selling_price,
                gct, stock_qty, group_id,
                disc1, disc2,
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            # Duplicate barcode — skip
            skipped += 1
            errors.append(f"  SKIP (dup barcode): {barcode}  {name}")

    conn.commit()
    conn.close()

    # ── 6. Report ────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"  ✅  Inserted:      {inserted}")
    print(f"  ⚠️   Skipped (dup): {skipped}")
    print(f"  ⚠️   No barcode:    {no_barcode}")
    if errors:
        print(f"\n  Duplicate barcodes:")
        for e in errors[:20]:
            print(e)
        if len(errors) > 20:
            print(f"  ... and {len(errors)-20} more")
    print(f"{'─'*60}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Import STOCK.DBF into the POS products.db"
    )
    parser.add_argument("dbf", help="Path to STOCK.DBF")
    parser.add_argument(
        "--db",
        default=os.path.join(os.path.dirname(__file__), "storedata", "products.db"),
        help="Path to products.db  (default: storedata/products.db)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.dbf):
        print(f"Error: DBF file not found: {args.dbf}")
        sys.exit(1)
    if not os.path.exists(args.db):
        print(f"Error: products.db not found: {args.db}")
        print("Run the POS system at least once to create the database, then re-run this script.")
        sys.exit(1)

    import_dbf(args.dbf, args.db)


if __name__ == "__main__":
    main()
