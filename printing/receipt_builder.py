"""
printing/receipt_builder.py
Fetches all data needed to print any receipt from the databases.
Returns structured dicts consumed by the formatter and printer modules.
"""

from datetime import datetime
from db import get_transactions_conn, get_business_conn


def get_business_info():
    """Return business info dict from business.db."""
    conn = get_business_conn()
    row  = conn.execute("""
        SELECT business_name, address, phone, receipt_footer,
               tax_percent, receipt_layout
        FROM business_info WHERE id = 1
    """).fetchone()
    conn.close()
    if not row:
        return {
            "business_name": "Merchant Retail POS",
            "address":        "",
            "phone":          "",
            "receipt_footer": "Thank you for your purchase!",
            "tax_percent":    16.5,
            "receipt_layout": "gct_column",   # 'simple' | 'gct_column'
        }
    return {
        "business_name":  row[0] or "Merchant Retail POS",
        "address":        row[1] or "",
        "phone":          row[2] or "",
        "receipt_footer": row[3] or "Thank you for your purchase!",
        "tax_percent":    row[4] or 16.5,
        "receipt_layout": row[5] or "gct_column",
    }


def build_sale_receipt(transaction_id):
    """
    Build receipt data dict for a completed sale.
    Returns None if transaction not found.
    """
    conn    = get_transactions_conn()
    cursor  = conn.cursor()

    # Transaction header
    cursor.execute("""
        SELECT id, cashier_name, date, time, subtotal,
               tax_amount, total, status
        FROM transactions WHERE id = ?
    """, (transaction_id,))
    tx = cursor.fetchone()
    if not tx:
        conn.close()
        return None

    tx_id, cashier, date, time, subtotal, tax_amount, total, status = tx

    # Line items
    cursor.execute("""
        SELECT product_name_snapshot, quantity,
               unit_price_snapshot, gct_applicable,
               discount_applied, line_total
        FROM transaction_items
        WHERE transaction_id = ?
        ORDER BY id
    """, (transaction_id,))
    raw_items = cursor.fetchall()
    conn.close()

    items = []
    for name, qty, unit_price, gct_applicable, discount, line_total in raw_items:
        gct_per_unit = round(unit_price * 0 if not gct_applicable
                             else unit_price * (_get_gct_rate() / 100), 2)
        gct_line     = round(gct_per_unit * qty, 2)
        items.append({
            "name":           name,
            "qty":            qty,
            "unit_price":     unit_price,
            "gct_applicable": bool(gct_applicable),
            "gct_line":       gct_line,
            "discount":       discount,
            "line_total":     line_total,
        })

    biz = get_business_info()

    return {
        "type":           "sale",
        "transaction_id": tx_id,
        "cashier":        cashier,
        "date":           date,
        "time":           time,
        "subtotal":       subtotal,
        "tax_amount":     tax_amount,
        "total":          total,
        "status":         status,
        "items":          items,
        "business":       biz,
        # Filled in at print time from checkout dialog
        "cash_tendered":  0.0,
        "change":         0.0,
    }


def build_void_receipt(transaction_id, reason, voided_by):
    """Build receipt data dict for a voided transaction."""
    data = build_sale_receipt(transaction_id)
    if not data:
        return None
    data["type"]      = "void"
    data["reason"]    = reason
    data["voided_by"] = voided_by
    data["void_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return data


def build_refund_receipt(transaction_id, refund_items, refund_total, reason, refunded_by):
    """
    Build receipt data dict for a refund.
    refund_items: list of dicts with name, qty, unit_price, line_total
    """
    data = build_sale_receipt(transaction_id)
    if not data:
        return None
    data["type"]          = "refund"
    data["reason"]        = reason
    data["refunded_by"]   = refunded_by
    data["refund_time"]   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["refund_items"]  = refund_items
    data["refund_total"]  = refund_total
    return data


def build_session_receipt(session_id):
    """Build receipt data dict for a session summary."""
    conn   = get_transactions_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, cashier_name, opened_at, closed_at,
               total_sales, total_gct, total_discount,
               transaction_count, status,
               opened_by_name, closed_by_name
        FROM cashing_sessions WHERE id = ?
    """, (session_id,))
    sess = cursor.fetchone()
    if not sess:
        conn.close()
        return None

    (sid, cashier, opened_at, closed_at, total_sales, total_gct,
     total_discount, tx_count, status, opened_by, closed_by) = sess

    # Transactions that belong to this cashier's login sessions which
    # started on or after the cashing session was opened.
    # We join through sessions (login) → transactions using cashier_id.
    cursor.execute("""
        SELECT t.id, t.date, t.time, t.total, t.status
        FROM transactions t
        INNER JOIN sessions s ON s.id = t.session_id
        WHERE s.cashier_id = (
            SELECT cashier_id FROM cashing_sessions WHERE id = ?
        )
          AND s.started_at >= ?
          AND (? IS NULL OR s.started_at <= ?)
        ORDER BY t.id DESC LIMIT 20
    """, (session_id, opened_at, closed_at, closed_at))
    transactions = [
        {"id": r[0], "date": r[1], "time": r[2],
         "total": r[3], "status": r[4]}
        for r in cursor.fetchall()
    ]
    conn.close()

    biz = get_business_info()

    return {
        "type":            "session",
        "session_id":      sid,
        "cashier":         cashier,
        "opened_at":       opened_at,
        "closed_at":       closed_at or "Still Open",
        "total_sales":     total_sales,
        "total_gct":       total_gct,
        "total_discount":  total_discount,
        "transaction_count": tx_count,
        "status":          status,
        "opened_by":       opened_by,
        "closed_by":       closed_by or "—",
        "transactions":    transactions,
        "business":        biz,
        "print_time":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _get_gct_rate():
    """Get current GCT rate from business.db."""
    conn = get_business_conn()
    row  = conn.execute(
        "SELECT tax_percent FROM business_info WHERE id=1"
    ).fetchone()
    conn.close()
    return row[0] if row else 16.5
