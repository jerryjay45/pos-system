"""
printing/thermal_printer.py
Sends formatted receipt text to an Epson TM-series thermal receipt printer
(TM-T20, TM-T82, TM-T88, TM-T20II/III) via the python-escpos library.

Paper: 80mm  →  48 printable columns at Font A (12x24 dot)

Connection auto-detect order:
  1. USB   -- tries all known Epson TM USB product IDs
  2. Serial -- /dev/ttyUSB0, /dev/ttyS0, COM1-COM4
  3. Network -- IP stored in business.db
"""

import sys

# -- Known Epson TM USB IDs ---------------------------------------------------
# vendor 0x04b8 = Seiko Epson Corp.
_EPSON_VENDOR = 0x04b8
_EPSON_TM_PRODUCTS = [
    0x0202, 0x0203, 0x0204, 0x0207,  # TM-T88 II/III/IV/V
    0x0215,                           # TM-T20
    0x0220,                           # TM-T82
    0x0300,                           # TM-T20II
    0x0305,                           # TM-T20III
    0x0404,                           # TM-T88VI
    0x0407,                           # TM-T30
]

# 80mm paper at Font A = 48 columns
COLS = 48


# -- Settings -----------------------------------------------------------------

def _get_printer_settings():
    """Read printer connection settings from business.db."""
    try:
        from db import get_business_conn
        conn = get_business_conn()
        row  = conn.execute("""
            SELECT thermal_connection, thermal_port,
                   thermal_vendor_id, thermal_product_id
            FROM business_info WHERE id = 1
        """).fetchone()
        conn.close()
        if row:
            return {
                "connection":  row[0] or "auto",
                "port":        row[1] or "",
                "vendor_id":   int(row[2]) if row[2] else _EPSON_VENDOR,
                "product_id":  int(row[3]) if row[3] else 0,
            }
    except Exception:
        pass
    return {"connection": "auto", "port": "", "vendor_id": _EPSON_VENDOR, "product_id": 0}


# -- Connection helpers --------------------------------------------------------

def _try_usb(vendor_id=_EPSON_VENDOR, product_id=0):
    try:
        from escpos.printer import Usb
    except ImportError:
        return None, "python-escpos not installed. Run: pip install python-escpos"

    ids_to_try = [product_id] if product_id else _EPSON_TM_PRODUCTS
    last_err = "No Epson TM USB device found"
    for pid in ids_to_try:
        try:
            p = Usb(vendor_id, pid, timeout=0, in_ep=0x82, out_ep=0x01)
            return p, None
        except Exception as e:
            last_err = str(e)
    return None, last_err


def _try_serial(port=""):
    try:
        from escpos.printer import Serial
    except ImportError:
        return None, "python-escpos not installed"

    ports = [port] if port else (
        ["COM1", "COM2", "COM3", "COM4"] if sys.platform == "win32"
        else ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyS0", "/dev/ttyS1"]
    )
    last_err = "No serial port found"
    for p_name in ports:
        try:
            p = Serial(devfile=p_name, baudrate=9600, bytesize=8,
                       parity="N", stopbits=1, timeout=1.0, dsrdtr=True)
            return p, None
        except Exception as e:
            last_err = str(e)
    return None, last_err


def _try_network(host=""):
    if not host:
        return None, "No network host configured"
    try:
        from escpos.printer import Network
        p = Network(host, port=9100, timeout=5)
        return p, None
    except ImportError:
        return None, "python-escpos not installed"
    except Exception as e:
        return None, str(e)


def auto_detect_printer():
    """Try USB -> Serial -> Network. Returns (printer, None) or (None, err)."""
    p, _ = _try_usb()
    if p: return p, None

    p, _ = _try_serial()
    if p: return p, None

    # Network only if a non-device host is stored in db
    try:
        from db import get_business_conn
        conn = get_business_conn()
        row  = conn.execute("SELECT thermal_port FROM business_info WHERE id=1").fetchone()
        conn.close()
        host = (row[0] or "").strip() if row else ""
        if host and not host.startswith("/dev/") and not host.upper().startswith("COM"):
            p, err = _try_network(host)
            if p: return p, None
    except Exception:
        pass

    return None, "No thermal printer detected (tried USB, serial, network)"


def _connect_printer(settings):
    t = settings.get("connection", "auto").lower()
    if t == "usb":     return _try_usb(settings["vendor_id"], settings["product_id"])
    if t == "serial":  return _try_serial(settings.get("port", ""))
    if t == "network": return _try_network(settings.get("port", ""))
    return auto_detect_printer()


# -- Raw ESC/POS commands -----------------------------------------------------

def _esc(b): return bytes(b)

ESC_INIT         = _esc([0x1b, 0x40])            # ESC @   initialize
ESC_FONT_A       = _esc([0x1b, 0x4d, 0x00])      # ESC M 0 font A
ESC_ALIGN_L      = _esc([0x1b, 0x61, 0x00])      # ESC a 0 left
ESC_ALIGN_C      = _esc([0x1b, 0x61, 0x01])      # ESC a 1 center
ESC_ALIGN_R      = _esc([0x1b, 0x61, 0x02])      # ESC a 2 right
ESC_BOLD_ON      = _esc([0x1b, 0x45, 0x01])      # ESC E 1
ESC_BOLD_OFF     = _esc([0x1b, 0x45, 0x00])      # ESC E 0
ESC_DH_ON        = _esc([0x1b, 0x21, 0x10])      # ESC ! double height
ESC_DH_OFF       = _esc([0x1b, 0x21, 0x00])      # ESC ! normal
ESC_FEED_4       = _esc([0x1b, 0x64, 0x04])      # ESC d 4  feed 4 lines
ESC_PARTIAL_CUT  = _esc([0x1d, 0x56, 0x42, 0x03])# GS V 66 3 partial cut
ESC_BEEP         = _esc([0x07])                  # BEL


def _line(text):
    """Encode a text line to cp437 bytes + newline."""
    return text.encode("cp437", errors="replace") + b"\n"


# -- Main print function -------------------------------------------------------

def print_text_thermal(text, cut=True):
    """
    Print formatted receipt text to the Epson TM thermal printer.

    Lines beginning with '===' are printed as bold dividers.
    Lines beginning with '---' are printed as plain dividers.
    Lines containing 'TOTAL:' or 'NET SALES:' are printed double-height.

    Args:
        text: str  -- full formatted receipt (newline-separated)
        cut:  bool -- partial-cut + beep after printing

    Returns:
        (True, None) on success
        (False, error_message) on failure
    """
    settings = _get_printer_settings()
    p, err   = _connect_printer(settings)
    if p is None:
        return False, f"Thermal printer not available: {err}"

    try:
        buf = bytearray()
        buf += ESC_INIT
        buf += ESC_FONT_A
        buf += ESC_ALIGN_L

        for raw_line in text.split("\n"):
            s = raw_line.strip()

            # === bold divider
            if s.startswith("==="):
                buf += ESC_BOLD_ON + ESC_ALIGN_C
                buf += _line("=" * COLS)
                buf += ESC_BOLD_OFF + ESC_ALIGN_L
                continue

            # --- thin divider
            if s.startswith("---"):
                buf += _line("-" * COLS)
                continue

            # TOTAL / NET SALES -- double-height bold
            if s.startswith("TOTAL:") or s.startswith("NET SALES:"):
                buf += ESC_BOLD_ON + ESC_DH_ON
                buf += _line(raw_line)
                buf += ESC_DH_OFF + ESC_BOLD_OFF
                continue

            # *** markers (VOID / REFUND banners) -- bold centered
            if s.startswith("***"):
                buf += ESC_BOLD_ON + ESC_ALIGN_C
                buf += _line(s)
                buf += ESC_BOLD_OFF + ESC_ALIGN_L
                continue

            # Business name: all-caps, centered, non-numeric -- bold centered
            if (s and s == s.upper() and len(s) > 4
                    and not any(c.isdigit() for c in s.replace("$","").replace(".","").replace("#","").replace(":","").replace(" ",""))
                    and s not in ("GCT", "PRODUCT") ):
                buf += ESC_BOLD_ON + ESC_ALIGN_C
                buf += _line(s)
                buf += ESC_BOLD_OFF + ESC_ALIGN_L
                continue

            # Normal line
            buf += _line(raw_line)

        if cut:
            buf += ESC_FEED_4
            buf += ESC_PARTIAL_CUT
            buf += ESC_BEEP

        p._raw(bytes(buf))
        p.close()
        return True, None

    except Exception as e:
        try: p.close()
        except Exception: pass
        return False, str(e)
