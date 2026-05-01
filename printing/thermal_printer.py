"""
printing/thermal_printer.py
Sends formatted receipt text to the Epson TM-U220D (USB impact printer)
via the python-escpos library.

Connection priority:
  1. USB (TM-U220D default)
  2. Serial (COM port — TM-U220B)
  3. Parallel (LPT — TM-U220A)
  4. Network (Ethernet models)

All connection details are read from business.db printer settings.
"""

import sys


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
                "connection":  row[0] or "usb",
                "port":        row[1] or "",
                "vendor_id":   row[2] or 0x04b8,   # Epson default vendor ID
                "product_id":  row[3] or 0x0202,   # TM-U220 USB product ID
            }
    except Exception:
        pass
    return {
        "connection":  "usb",
        "port":        "",
        "vendor_id":   0x04b8,
        "product_id":  0x0202,
    }


def _connect_printer(settings):
    """
    Try to connect to the thermal printer.
    Returns an escpos printer object or None.
    """
    try:
        from escpos import printer as escpos_printer
    except ImportError:
        return None, "python-escpos not installed. Run: pip install python-escpos"

    conn_type = settings.get("connection", "usb").lower()

    try:
        if conn_type == "usb":
            p = escpos_printer.Usb(
                settings["vendor_id"],
                settings["product_id"],
                timeout=0,
                in_ep=0x82,
                out_ep=0x01
            )
            return p, None

        elif conn_type == "serial":
            port = settings.get("port", "COM1")
            p = escpos_printer.Serial(
                devfile=port,
                baudrate=9600,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=1.0,
                dsrdtr=True
            )
            return p, None

        elif conn_type == "parallel":
            port = settings.get("port", "LPT1")
            p = escpos_printer.LP(port)
            return p, None

        elif conn_type == "network":
            host = settings.get("port", "192.168.1.100")
            p = escpos_printer.Network(host, port=9100, timeout=5)
            return p, None

        else:
            return None, f"Unknown connection type: {conn_type}"

    except Exception as e:
        return None, str(e)


def auto_detect_printer():
    """
    Auto-detect the thermal printer by trying USB first,
    then Serial (COM1-COM4), then Network.
    Returns (printer_object, None) on success or (None, error_msg).
    """
    try:
        from escpos import printer as escpos_printer
    except ImportError:
        return None, "python-escpos not installed"

    # Try USB first (TM-U220D)
    try:
        p = escpos_printer.Usb(0x04b8, 0x0202, timeout=0)
        return p, None
    except Exception:
        pass

    # Try common serial ports
    ports = (["COM1", "COM2", "COM3", "COM4"]
             if sys.platform == "win32"
             else ["/dev/ttyS0", "/dev/ttyS1", "/dev/ttyUSB0"])
    for port in ports:
        try:
            p = escpos_printer.Serial(devfile=port, baudrate=9600,
                                      timeout=1.0, dsrdtr=True)
            return p, None
        except Exception:
            continue

    # Try parallel
    lpt = "LPT1" if sys.platform == "win32" else "/dev/lp0"
    try:
        p = escpos_printer.LP(lpt)
        return p, None
    except Exception:
        pass

    return None, "No thermal printer detected"


def print_text_thermal(text_lines, cut=True):
    """
    Print a block of text to the thermal/impact printer.

    Args:
        text_lines: str — the full formatted receipt text (newline-separated)
        cut: bool — feed and beep after print (TM-U220 tears, no auto-cut)

    Returns:
        (True, None) on success
        (False, error_message) on failure
    """
    settings = _get_printer_settings()
    p, err   = _connect_printer(settings)

    if p is None:
        # Try auto-detect as fallback
        p, err = auto_detect_printer()

    if p is None:
        return False, f"Thermal printer not available: {err}"

    try:
        # ESC/POS initialise
        p.hw("INIT")

        # TM-U220 is 40 columns — set font A (normal)
        p.set(align="left", font="a", bold=False, underline=0,
              width=1, height=1)

        # Print each line
        for line in text_lines.split("\n"):
            p.text(line + "\n")

        # Feed and beep (impact printers don't auto-cut)
        if cut:
            p.text("\n\n\n")   # feed 3 lines for tear
            p.buzzer()         # beep to alert cashier

        p.close()
        return True, None

    except Exception as e:
        try:
            p.close()
        except Exception:
            pass
        return False, str(e)
