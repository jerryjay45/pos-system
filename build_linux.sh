#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build_linux.sh
# Build script for Merchant Retail POS on Arch Linux.
# Produces a one-folder bundle in dist/MerchantPOS/
#
# Usage:
#   chmod +x build_linux.sh
#   ./build_linux.sh
#
# Output:
#   dist/MerchantPOS/MerchantPOS   — run this binary
# ─────────────────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}  $*"; }
info() { echo -e "${BOLD}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; }

echo
echo "============================================================"
echo "  Merchant Retail POS — Linux Build"
echo "============================================================"
echo

# ── Check Python ──────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    err "python3 not found. Install: sudo pacman -S python"
    exit 1
fi
ok "Python: $(python3 --version)"

# ── Check / install PyInstaller ───────────────────────────────────────────────
if ! python3 -m PyInstaller --version &>/dev/null; then
    info "Installing PyInstaller..."
    pip install pyinstaller --break-system-packages
fi
ok "PyInstaller: $(python3 -m PyInstaller --version)"

# ── Install dependencies ──────────────────────────────────────────────────────
info "Installing / verifying dependencies..."
pip install \
    PyQt6 \
    psycopg2-binary \
    python-escpos \
    Pillow \
    python-barcode \
    pyserial \
    pyusb \
    --break-system-packages \
    --quiet
ok "Dependencies ready"

# ── Clean previous build ──────────────────────────────────────────────────────
info "Cleaning previous build..."
rm -rf build/MerchantPOS dist/MerchantPOS
ok "Clean done"

# ── Build ─────────────────────────────────────────────────────────────────────
info "Running PyInstaller (this takes 1-3 minutes)..."
echo
python3 -m PyInstaller merchant_pos.spec --noconfirm
echo

# ── Post-build setup ──────────────────────────────────────────────────────────
info "Setting up storedata folder..."
mkdir -p dist/MerchantPOS/storedata
ok "storedata/ created"

# Copy assets (icon)
mkdir -p dist/MerchantPOS/assets
[ -f assets/merchant_pos_256.png ] && cp assets/merchant_pos_256.png dist/MerchantPOS/assets/
[ -f assets/merchant_pos_512.png ] && cp assets/merchant_pos_512.png dist/MerchantPOS/assets/
[ -f assets/merchant_pos.ico ]     && cp assets/merchant_pos.ico     dist/MerchantPOS/assets/
ok "Assets copied"

# ── .desktop entry (Linux application launcher) ────────────────────────────
DESKTOP_FILE="dist/MerchantPOS/merchant_pos.desktop"
INSTALL_DIR="$(pwd)/dist/MerchantPOS"
cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Merchant Retail POS
Comment=Point of Sale System
Exec=${INSTALL_DIR}/MerchantPOS
Icon=${INSTALL_DIR}/assets/merchant_pos_256.png
Terminal=false
Categories=Office;Finance;
Keywords=pos;retail;sales;cashier;
StartupWMClass=MerchantPOS
DESKTOP
chmod +x "$DESKTOP_FILE"
ok ".desktop entry created → $DESKTOP_FILE"
info "To install as a system app:"
echo "  cp $DESKTOP_FILE ~/.local/share/applications/"
echo "  cp assets/merchant_pos_256.png ~/.local/share/icons/"

# Make the binary executable
chmod +x dist/MerchantPOS/MerchantPOS

# ── USB printer udev rule ─────────────────────────────────────────────────────
UDEV_RULE='/etc/udev/rules.d/99-epson-tm.rules'
if [ ! -f "$UDEV_RULE" ]; then
    warn "USB thermal printer udev rule not found."
    info "To allow non-root USB printer access, run:"
    echo
    echo '  sudo tee /etc/udev/rules.d/99-epson-tm.rules << EOF'
    echo '  # Epson TM series thermal printers'
    echo '  SUBSYSTEM=="usb", ATTRS{idVendor}=="04b8", MODE="0666", GROUP="lp"'
    echo '  EOF'
    echo '  sudo udevadm control --reload-rules && sudo udevadm trigger'
    echo '  sudo usermod -aG lp $USER   # then log out and back in'
    echo
fi

# ── Report ────────────────────────────────────────────────────────────────────
echo
echo "============================================================"
echo -e "  ${GREEN}BUILD COMPLETE${NC}"
echo "============================================================"
echo
echo "  Output:  dist/MerchantPOS/MerchantPOS"
echo
echo "  Run:     ./dist/MerchantPOS/MerchantPOS"
echo
echo "  To cross-compile for Windows from Linux, install"
echo "  Wine + windows Python + run build_windows.bat inside Wine,"
echo "  or build natively on a Windows machine."
echo "============================================================"
echo
