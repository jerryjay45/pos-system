"""
printing/formatter.py
Converts a receipt data dict into formatted text strings.

Thermal output: 40-column plain text (TM-U220 impact printer)
Normal output:  wider formatted text for QPrinter (A4/Letter/Legal)

Two receipt layouts:
  'simple'     — name + qty x price + line total
  'gct_column' — 3 columns: product info | GCT | TOTAL (default)
"""

# ── Column widths ─────────────────────────────────────────────────────────────
THERMAL_WIDTH   = 40
NORMAL_WIDTH    = 60    # wider for A4 normal printer


# ── Helpers ───────────────────────────────────────────────────────────────────

def _center(text, width):
    return text.center(width)

def _ljust(text, width):
    return text[:width].ljust(width)

def _rjust(text, width):
    return text[-width:].rjust(width)

def _divider(char="-", width=THERMAL_WIDTH):
    return char * width

def _col3(left, mid, right, width=THERMAL_WIDTH):
    """Format 3 columns across the full width."""
    mid_width   = len(mid)
    right_width = len(right)
    left_width  = width - mid_width - right_width - 2
    return f"{left[:left_width].ljust(left_width)}  {mid}{right}"

def _col2(left, right, width=THERMAL_WIDTH):
    """Format 2 columns: left-aligned label, right-aligned value."""
    right_str = str(right)
    left_str  = str(left)
    pad       = width - len(left_str) - len(right_str)
    if pad < 1:
        pad = 1
    return left_str + " " * pad + right_str


# ── Main format functions ──────────────────────────────────────────────────────

def format_sale(data, layout=None, width=THERMAL_WIDTH):
    """
    Format a sale receipt.
    layout: 'simple' or 'gct_column'. Falls back to data['business']['receipt_layout'].
    """
    if layout is None:
        layout = data["business"].get("receipt_layout", "gct_column")

    lines = []
    biz   = data["business"]

    # ── Header ────────────────────────────────────────────────────────
    lines.append(_divider("=", width))
    lines.append(_center(biz["business_name"].upper(), width))
    if biz["address"]:
        lines.append(_center(biz["address"], width))
    if biz["phone"]:
        lines.append(_center(f"Tel: {biz['phone']}", width))
    lines.append(_divider("=", width))
    lines.append(_col2(f"Date: {data['date']}", f"Time: {data['time']}", width))
    lines.append(_col2(f"Receipt #: {data['transaction_id']}", "", width).rstrip())
    lines.append(f"Cashier: {data['cashier']}")
    lines.append(_divider("-", width))

    # ── Items ─────────────────────────────────────────────────────────
    if layout == "gct_column":
        lines += _format_items_gct_column(data["items"], width)
    else:
        lines += _format_items_simple(data["items"], width)

    lines.append(_divider("-", width))

    # ── Totals ────────────────────────────────────────────────────────
    lines.append(_col2("Subtotal:",      f"${data['subtotal']:.2f}", width))
    lines.append(_col2(
        f"GCT ({biz['tax_percent']:.1f}%):", f"${data['tax_amount']:.2f}", width
    ))
    discount = sum(i.get("discount", 0) * i["qty"] for i in data["items"])
    if discount > 0:
        lines.append(_col2("Discount:",  f"-${discount:.2f}", width))
    lines.append(_divider("-", width))
    lines.append(_col2("TOTAL:",         f"${data['total']:.2f}", width))
    lines.append(_divider("-", width))

    # ── Payment ───────────────────────────────────────────────────────
    if data.get("cash_tendered", 0) > 0:
        lines.append(_col2("Cash:",      f"${data['cash_tendered']:.2f}", width))
        lines.append(_col2("Change:",    f"${data['change']:.2f}", width))

    # ── Footer ────────────────────────────────────────────────────────
    lines.append(_divider("=", width))
    if biz["receipt_footer"]:
        lines.append(_center(biz["receipt_footer"], width))
    lines.append(_divider("=", width))
    lines.append("")   # trailing blank for tear line

    return "\n".join(lines)


def format_void(data, width=THERMAL_WIDTH):
    """Format a void receipt."""
    lines = []
    biz   = data["business"]

    lines.append(_divider("=", width))
    lines.append(_center(biz["business_name"].upper(), width))
    lines.append(_divider("=", width))
    lines.append(_center("*** VOID RECEIPT ***", width))
    lines.append(_divider("-", width))
    lines.append(f"Original Receipt #: {data['transaction_id']}")
    lines.append(f"Date:     {data['date']}  {data['time']}")
    lines.append(f"Cashier:  {data['cashier']}")
    lines.append(_divider("-", width))
    lines.append(f"Voided by: {data['voided_by']}")
    lines.append(f"Void time: {data['void_time']}")
    lines.append(f"Reason:    {data['reason']}")
    lines.append(_divider("-", width))
    lines.append(_col2("Original Total:", f"${data['total']:.2f}", width))
    lines.append(_divider("=", width))
    lines.append(_center("TRANSACTION VOIDED", width))
    lines.append(_divider("=", width))
    lines.append("")

    return "\n".join(lines)


def format_refund(data, width=THERMAL_WIDTH):
    """Format a refund receipt."""
    lines = []
    biz   = data["business"]

    lines.append(_divider("=", width))
    lines.append(_center(biz["business_name"].upper(), width))
    lines.append(_divider("=", width))
    lines.append(_center("*** REFUND RECEIPT ***", width))
    lines.append(_divider("-", width))
    lines.append(f"Original Receipt #: {data['transaction_id']}")
    lines.append(f"Date:      {data['date']}  {data['time']}")
    lines.append(f"Cashier:   {data['cashier']}")
    lines.append(_divider("-", width))
    lines.append(f"Refunded by: {data['refunded_by']}")
    lines.append(f"Refund time: {data['refund_time']}")
    lines.append(f"Reason:      {data['reason']}")
    lines.append(_divider("-", width))

    # Refunded items
    for item in data.get("refund_items", []):
        lines.append(f"  {item['name']}")
        lines.append(_col2(
            f"    {item['qty']} x ${item['unit_price']:.2f}",
            f"${item['line_total']:.2f}", width
        ))

    lines.append(_divider("-", width))
    lines.append(_col2("REFUND TOTAL:", f"${data['refund_total']:.2f}", width))
    lines.append(_divider("=", width))
    lines.append(_center("REFUND ISSUED", width))
    lines.append(_divider("=", width))
    lines.append("")

    return "\n".join(lines)


def format_session(data, width=THERMAL_WIDTH):
    """Format a session summary receipt."""
    lines = []
    biz   = data["business"]

    lines.append(_divider("=", width))
    lines.append(_center(biz["business_name"].upper(), width))
    lines.append(_divider("=", width))
    lines.append(_center("SESSION SUMMARY", width))
    lines.append(_divider("-", width))
    lines.append(f"Session #:  {data['session_id']}")
    lines.append(f"Cashier:    {data['cashier']}")
    lines.append(f"Opened:     {data['opened_at']}")
    lines.append(f"Closed:     {data['closed_at']}")
    lines.append(f"Opened by:  {data['opened_by']}")
    lines.append(f"Closed by:  {data['closed_by']}")
    lines.append(_divider("-", width))
    lines.append(_col2("Transactions:",  str(data["transaction_count"]), width))
    lines.append(_col2("Total Sales:",   f"${data['total_sales']:.2f}", width))
    lines.append(_col2("Total GCT:",     f"${data['total_gct']:.2f}", width))
    lines.append(_col2("Total Discounts:", f"${data['total_discount']:.2f}", width))
    net = data["total_sales"] - data["total_gct"] - data["total_discount"]
    lines.append(_divider("-", width))
    lines.append(_col2("NET SALES:",     f"${net:.2f}", width))
    lines.append(_divider("=", width))

    # Last transactions list
    if data.get("transactions"):
        lines.append("Recent Transactions:")
        lines.append(_divider("-", width))
        for tx in data["transactions"][:15]:
            status_tag = "" if tx["status"] == "completed" else f" [{tx['status'].upper()}]"
            lines.append(_col2(
                f"  #{tx['id']} {tx['time']}{status_tag}",
                f"${tx['total']:.2f}", width
            ))
        lines.append(_divider("-", width))

    lines.append(f"Printed: {data['print_time']}")
    lines.append(_divider("=", width))
    lines.append("")

    return "\n".join(lines)


# ── Item formatters ───────────────────────────────────────────────────────────

def _format_items_simple(items, width):
    """Simple layout: name + qty x price = line total."""
    lines = []
    for item in items:
        name = item["name"]
        if len(name) > width:
            name = name[:width - 3] + "..."
        lines.append(name)
        qty_price = f"  {item['qty']} x ${item['unit_price']:.2f}"
        lines.append(_col2(qty_price, f"${item['line_total']:.2f}", width))
    return lines


def _format_items_gct_column(items, width):
    """
    3-column layout:
      PRODUCT (left)         GCT (mid-right)   TOTAL (right)
    Column widths scale to receipt width.
    """
    # Right column = 7 chars "$999.99", GCT col = 8 chars "$999.99 "
    right_w = 8
    gct_w   = 8
    left_w  = width - gct_w - right_w

    lines = []

    # Column header
    hdr_gct   = "GCT".rjust(gct_w)
    hdr_total = "TOTAL".rjust(right_w)
    lines.append(f"{'PRODUCT'.ljust(left_w)}{hdr_gct}{hdr_total}")
    lines.append("-" * width)

    for item in items:
        # Product name line
        name = item["name"]
        if len(name) > left_w:
            name = name[:left_w - 2] + ".."
        lines.append(name)

        # Qty x price line with GCT and total columns
        qty_price = f"  {item['qty']} x ${item['unit_price']:.2f}"

        if item["gct_applicable"] and item["gct_line"] > 0:
            gct_str = f"${item['gct_line']:.2f}".rjust(gct_w)
        else:
            gct_str = "---".rjust(gct_w)

        total_str = f"${item['line_total']:.2f}".rjust(right_w)

        # Pad qty_price to left_w
        qty_price = qty_price[:left_w].ljust(left_w)
        lines.append(f"{qty_price}{gct_str}{total_str}")

    return lines
