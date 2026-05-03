#!/usr/bin/env bash
# =============================================================================
# build_windows.sh
# Cross-compile Merchant Retail POS for Windows 10/11 from Linux
# Supports: Arch Linux, Fedora, Debian/Ubuntu
#
# Usage:
#   chmod +x build_windows.sh
#   ./build_windows.sh
#
# Output:
#   dist/windows/MerchantPOS_Setup.exe   ← Inno Setup installer
#   dist/windows/MerchantPOS_Portable/   ← Portable folder (no installer)
#
# Requirements installed automatically by this script:
#   - Wine (to run Windows Python + PyInstaller)
#   - Python 3.11 for Windows (downloaded automatically)
#   - PyInstaller (installed into Wine Python)
#   - Inno Setup 6 (downloaded, run via Wine)
# =============================================================================

set -euo pipefail

# ── Colour output ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step()    { echo -e "\n${BOLD}▶ $*${NC}"; }

# ── Configuration ─────────────────────────────────────────────────────────────
APP_NAME="MerchantPOS"
APP_VERSION="1.0.0"
APP_DISPLAY="Merchant Retail POS"
PUBLISHER="Merchant Retail"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build_win"
DIST_DIR="$SCRIPT_DIR/dist/windows"
WINE_PREFIX="$BUILD_DIR/wine_prefix"
WIN_PYTHON_VERSION="3.11.9"
WIN_PYTHON_URL="https://www.python.org/ftp/python/${WIN_PYTHON_VERSION}/python-${WIN_PYTHON_VERSION}-amd64.exe"
WIN_PYTHON_INSTALLER="$BUILD_DIR/python-${WIN_PYTHON_VERSION}-amd64.exe"
INNO_URL="https://jrsoftware.org/download.php/is.exe"
INNO_INSTALLER="$BUILD_DIR/inno_setup.exe"
WINE_PYTHON="wine python"

mkdir -p "$BUILD_DIR" "$DIST_DIR"

# ── Step 1: Detect distro and install Wine ────────────────────────────────────
step "Detecting Linux distribution"

if command -v wine &>/dev/null; then
    success "Wine already installed: $(wine --version)"
else
    info "Installing Wine..."
    if command -v pacman &>/dev/null; then
        # Arch Linux
        info "Arch Linux detected"
        sudo pacman -Sy --noconfirm wine wine-mono wine-gecko
    elif command -v dnf &>/dev/null; then
        # Fedora
        info "Fedora detected"
        sudo dnf install -y wine
    elif command -v apt-get &>/dev/null; then
        # Debian/Ubuntu
        info "Debian/Ubuntu detected"
        sudo dpkg --add-architecture i386
        sudo apt-get update -q
        sudo apt-get install -y wine wine64 wine32
    else
        error "Unsupported distro. Install Wine manually then re-run."
    fi
    success "Wine installed: $(wine --version)"
fi

# ── Step 2: Set up Wine prefix (64-bit Windows) ───────────────────────────────
step "Setting up Wine prefix"
export WINEPREFIX="$WINE_PREFIX"
export WINEARCH=win64

if [ ! -f "$WINE_PREFIX/system.reg" ]; then
    info "Initialising Wine prefix at $WINE_PREFIX ..."
    wineboot --init 2>/dev/null || true
    sleep 3
    success "Wine prefix ready"
else
    success "Wine prefix already exists"
fi

# ── Step 3: Install Windows Python ───────────────────────────────────────────
step "Installing Windows Python $WIN_PYTHON_VERSION"

WIN_PYTHON_EXE="$WINE_PREFIX/drive_c/Python311/python.exe"
if [ ! -f "$WIN_PYTHON_EXE" ]; then
    if [ ! -f "$WIN_PYTHON_INSTALLER" ]; then
        info "Downloading Python $WIN_PYTHON_VERSION for Windows..."
        curl -L -o "$WIN_PYTHON_INSTALLER" "$WIN_PYTHON_URL"
        success "Downloaded"
    fi
    info "Installing Python into Wine (this may take a minute)..."
    wine "$WIN_PYTHON_INSTALLER" /quiet InstallAllUsers=1 \
        TargetDir='C:\Python311' PrependPath=1 2>/dev/null || true
    sleep 5
    success "Python $WIN_PYTHON_VERSION installed in Wine"
else
    success "Windows Python already installed in Wine"
fi

WINE_PY="wine $WINE_PREFIX/drive_c/Python311/python.exe"
WINE_PIP="wine $WINE_PREFIX/drive_c/Python311/python.exe -m pip"

# ── Step 4: Install Python dependencies into Wine Python ─────────────────────
step "Installing Python packages into Wine Python"

info "Upgrading pip..."
$WINE_PIP install --upgrade pip --quiet

info "Installing PyQt6..."
$WINE_PIP install PyQt6==6.11.0 --quiet

info "Installing other dependencies..."
$WINE_PIP install \
    python-barcode \
    Pillow \
    psycopg2-binary \
    python-escpos \
    pyusb \
    pyserial \
    pyinstaller \
    --quiet

success "All packages installed"

# ── Step 5: Create PyInstaller spec file ──────────────────────────────────────
step "Creating PyInstaller spec"

# Verify icon exists before we embed it in the spec
if [ ! -f "$SCRIPT_DIR/assets/merchant_pos.ico" ]; then
    error "assets/merchant_pos.ico not found. Cannot embed icon in EXE."
fi

# Convert the Linux path to a Wine/Windows path for the icon
ICO_WIN_PATH=$(winepath -w "$SCRIPT_DIR/assets/merchant_pos.ico" 2>/dev/null \
    || echo "Z:${SCRIPT_DIR}/assets/merchant_pos.ico" | sed 's|/|\\|g')

cat > "$BUILD_DIR/MerchantPOS.spec" << SPEC
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

qt_datas, qt_binaries, qt_imports = collect_all('PyQt6')
datas += qt_datas
binaries += qt_binaries
hiddenimports += qt_imports

hiddenimports += collect_submodules('db')
hiddenimports += collect_submodules('ui')
hiddenimports += collect_submodules('printing')
hiddenimports += collect_submodules('core')
hiddenimports += ['psycopg2', 'usb', 'serial', 'PIL']

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas + [
        ('assets', 'assets'),
        ('README.md', '.'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MerchantPOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon='${ICO_WIN_PATH}',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll',
        'Qt6PrintSupport.dll', 'qwindows.dll',
    ],
    name='MerchantPOS',
)
SPEC

# Copy spec to project root so Wine PyInstaller can find all source files
cp "$BUILD_DIR/MerchantPOS.spec" "$SCRIPT_DIR/MerchantPOS.spec"
success "Spec file created (icon: $ICO_WIN_PATH)"

# ── Step 6: Run PyInstaller via Wine ─────────────────────────────────────────
step "Running PyInstaller (building Windows EXE)"

info "This will take several minutes..."
cd "$SCRIPT_DIR"

wine "$WINE_PREFIX/drive_c/Python311/Scripts/pyinstaller.exe" \
    --clean \
    --noconfirm \
    MerchantPOS.spec \
    2>&1 | tail -30

# Move output to dist/windows
if [ -d "$SCRIPT_DIR/dist/MerchantPOS" ]; then
    rm -rf "$DIST_DIR/MerchantPOS_Portable"
    mv "$SCRIPT_DIR/dist/MerchantPOS" "$DIST_DIR/MerchantPOS_Portable"
    success "Portable build → $DIST_DIR/MerchantPOS_Portable/"
else
    error "PyInstaller failed — no dist/MerchantPOS folder found"
fi

# Copy assets folder into portable build so the icon is available at runtime
# and accessible to Inno Setup during installer compilation
mkdir -p "$DIST_DIR/MerchantPOS_Portable/assets"
cp "$SCRIPT_DIR/assets/merchant_pos.ico"     "$DIST_DIR/MerchantPOS_Portable/assets/"
cp "$SCRIPT_DIR/assets/merchant_pos_128.png" "$DIST_DIR/MerchantPOS_Portable/assets/" 2>/dev/null || true
cp "$SCRIPT_DIR/assets/merchant_pos_256.png" "$DIST_DIR/MerchantPOS_Portable/assets/" 2>/dev/null || true
cp "$SCRIPT_DIR/assets/merchant_pos_512.png" "$DIST_DIR/MerchantPOS_Portable/assets/" 2>/dev/null || true
success "Assets copied to portable folder"

# Ensure storedata folder exists in portable build
mkdir -p "$DIST_DIR/MerchantPOS_Portable/storedata"

# Clean up spec from project root
rm -f "$SCRIPT_DIR/MerchantPOS.spec"

# ── Step 7: Create Inno Setup installer ───────────────────────────────────────
step "Creating Windows installer with Inno Setup"

INNO_EXE="$WINE_PREFIX/drive_c/Program Files (x86)/Inno Setup 6/ISCC.exe"
if [ ! -f "$INNO_EXE" ]; then
    if [ ! -f "$INNO_INSTALLER" ]; then
        info "Downloading Inno Setup..."
        curl -L -o "$INNO_INSTALLER" "$INNO_URL"
    fi
    info "Installing Inno Setup into Wine..."
    wine "$INNO_INSTALLER" /VERYSILENT /SUPPRESSMSGBOXES 2>/dev/null || true
    sleep 5
    success "Inno Setup installed"
else
    success "Inno Setup already installed"
fi

# Convert Linux paths to Wine/Windows paths for use inside the .iss file
PORTABLE_WIN_PATH=$(winepath -w "$DIST_DIR/MerchantPOS_Portable" 2>/dev/null \
    || echo "Z:${DIST_DIR}/MerchantPOS_Portable" | sed 's|/|\\|g')
OUTPUT_WIN_PATH=$(winepath -w "$DIST_DIR" 2>/dev/null \
    || echo "Z:${DIST_DIR}" | sed 's|/|\\|g')
ICO_WIN_PATH_PORTABLE=$(winepath -w "$DIST_DIR/MerchantPOS_Portable/assets/merchant_pos.ico" 2>/dev/null \
    || echo "Z:${DIST_DIR}/MerchantPOS_Portable/assets/merchant_pos.ico" | sed 's|/|\\|g')

ISS_FILE="$BUILD_DIR/installer.iss"

cat > "$ISS_FILE" << ISS
[Setup]
AppName=${APP_DISPLAY}
AppVersion=${APP_VERSION}
AppVerName=${APP_DISPLAY} v${APP_VERSION}
AppPublisher=${PUBLISHER}
DefaultDirName={autopf}\\${APP_NAME}
DefaultGroupName=${APP_DISPLAY}
AllowNoIcons=yes
OutputDir=${OUTPUT_WIN_PATH}
OutputBaseFilename=${APP_NAME}_Setup_v${APP_VERSION}
SetupIconFile=${ICO_WIN_PATH_PORTABLE}
UninstallDisplayIcon={app}\\assets\\merchant_pos.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
PrivilegesRequired=admin
DisableProgramGroupPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "${PORTABLE_WIN_PATH}\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\${APP_DISPLAY}";           Filename: "{app}\\MerchantPOS.exe"; IconFilename: "{app}\\assets\\merchant_pos.ico"
Name: "{group}\\Uninstall ${APP_DISPLAY}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\\${APP_DISPLAY}";     Filename: "{app}\\MerchantPOS.exe"; IconFilename: "{app}\\assets\\merchant_pos.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\\MerchantPOS.exe"; Description: "{cm:LaunchProgram,${APP_DISPLAY}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\\storedata"
ISS

info "Compiling installer..."
ISS_WIN_PATH=$(winepath -w "$ISS_FILE" 2>/dev/null \
    || echo "Z:${ISS_FILE}" | sed 's|/|\\|g')
wine "$INNO_EXE" "$ISS_WIN_PATH" 2>/dev/null || warn "Inno Setup compilation had warnings"

INSTALLER_FILE="$DIST_DIR/${APP_NAME}_Setup_v${APP_VERSION}.exe"
if [ -f "$INSTALLER_FILE" ]; then
    success "Installer → $INSTALLER_FILE"
else
    warn "Installer file not found at expected path — check $DIST_DIR"
fi

# ── Step 8: Build import_stock_dbf.exe separately ────────────────────────────
step "Building import_stock_dbf.exe (standalone)"

wine "$WINE_PREFIX/drive_c/Python311/Scripts/pyinstaller.exe" \
    --onefile \
    --console \
    --name import_stock_dbf \
    --noconfirm \
    "$SCRIPT_DIR/import_stock_dbf.py" \
    2>&1 | tail -10

if [ -f "$SCRIPT_DIR/dist/import_stock_dbf.exe" ]; then
    mv "$SCRIPT_DIR/dist/import_stock_dbf.exe" "$DIST_DIR/import_stock_dbf.exe"
    success "import_stock_dbf.exe → $DIST_DIR/import_stock_dbf.exe"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  BUILD COMPLETE${NC}"
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Portable:   ${CYAN}$DIST_DIR/MerchantPOS_Portable/${NC}"
if [ -f "$INSTALLER_FILE" ]; then
echo -e "  Installer:  ${CYAN}$INSTALLER_FILE${NC}"
fi
echo -e "  DBF tool:   ${CYAN}$DIST_DIR/import_stock_dbf.exe${NC}"
echo ""
echo -e "  To test in Wine:"
echo -e "  ${YELLOW}wine \"$DIST_DIR/MerchantPOS_Portable/MerchantPOS.exe\"${NC}"
echo ""
