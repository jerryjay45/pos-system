@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM build_windows.bat
REM One-click build script for Merchant Retail POS on Windows.
REM
REM Requirements (run once before building):
REM   pip install pyinstaller pyqt6 psycopg2-binary python-escpos Pillow python-barcode
REM
REM Usage:
REM   Double-click build_windows.bat   OR   run from cmd/PowerShell
REM
REM Output:
REM   dist\MerchantPOS\MerchantPOS.exe  — distribute this entire folder
REM ─────────────────────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion
title Merchant POS — Windows Build

echo.
echo ============================================================
echo   Merchant Retail POS — Windows Build
echo ============================================================
echo.

REM ── Check Python is available ─────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found

REM ── Check PyInstaller is installed ────────────────────────────────────────
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)
echo [OK] PyInstaller found

REM ── Install / verify all dependencies ────────────────────────────────────
echo.
echo [INFO] Installing / verifying dependencies...
pip install ^
    PyQt6 ^
    psycopg2-binary ^
    python-escpos ^
    Pillow ^
    python-barcode ^
    pyserial ^
    pyusb ^
    --quiet
if errorlevel 1 (
    echo [WARN] Some dependencies may have failed — build will continue.
)
echo [OK] Dependencies ready

REM ── Clean previous build ──────────────────────────────────────────────────
echo.
echo [INFO] Cleaning previous build...
if exist build\MerchantPOS   rmdir /s /q build\MerchantPOS
if exist dist\MerchantPOS    rmdir /s /q dist\MerchantPOS
echo [OK] Clean done

REM ── Run PyInstaller ───────────────────────────────────────────────────────
echo.
echo [INFO] Running PyInstaller...
echo        This takes 1-3 minutes on first build.
echo.

pyinstaller merchant_pos.spec --noconfirm

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed. Check output above.
    pause
    exit /b 1
)

REM ── Post-build: copy storedata placeholder ───────────────────────────────
echo.
echo [INFO] Setting up storedata folder...
if not exist dist\MerchantPOS\storedata (
    mkdir dist\MerchantPOS\storedata
)

REM ── Post-build: copy utility scripts ─────────────────────────────────────
if exist import_stock_dbf.py (
    copy /y import_stock_dbf.py dist\MerchantPOS\ >nul
)
if exist README.md (
    copy /y README.md dist\MerchantPOS\ >nul
)

REM ── Post-build: check for libusb ─────────────────────────────────────────
echo.
if exist "C:\Windows\System32\libusb-1.0.dll" (
    echo [INFO] Copying libusb-1.0.dll for USB thermal printer...
    copy /y "C:\Windows\System32\libusb-1.0.dll" dist\MerchantPOS\ >nul
    echo [OK]  libusb-1.0.dll copied
) else if exist "C:\Windows\SysWOW64\libusb-1.0.dll" (
    echo [INFO] Copying libusb-1.0.dll (SysWOW64)...
    copy /y "C:\Windows\SysWOW64\libusb-1.0.dll" dist\MerchantPOS\ >nul
    echo [OK]  libusb-1.0.dll copied
) else (
    echo [WARN] libusb-1.0.dll not found.
    echo        USB thermal printer may not work without it.
    echo        Download from https://libusb.info and place in dist\MerchantPOS\
)

REM ── Report ───────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo   BUILD COMPLETE
echo ============================================================
echo.
echo   Output folder:  dist\MerchantPOS\
echo   Executable:     dist\MerchantPOS\MerchantPOS.exe
echo.
echo   To distribute: copy the entire dist\MerchantPOS\ folder
echo   to the target machine. No Python installation needed.
echo.
echo   First run creates storedata\ with fresh databases.
echo ============================================================
echo.

REM Open the output folder in Explorer
explorer dist\MerchantPOS

pause
