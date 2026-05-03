@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM build_windows.bat
REM One-click build script for Merchant Retail POS on Windows.
REM
REM Produces:
REM   dist\MerchantPOS\MerchantPOS.exe        — portable folder
REM   dist\MerchantPOS_Setup_v1.0.0.exe       — installer (Start Menu + Desktop icon)
REM
REM Requirements (installed automatically if missing):
REM   pip install pyinstaller pyqt6 psycopg2-binary python-escpos Pillow python-barcode
REM   Inno Setup 6 (downloaded automatically if not installed)
REM ─────────────────────────────────────────────────────────────────────────────

setlocal enabledelayedexpansion
title Merchant POS — Windows Build

set APP_NAME=MerchantPOS
set APP_DISPLAY=Merchant Retail POS
set APP_VERSION=1.0.0
set APP_PUBLISHER=Merchant Retail
set INNO_URL=https://jrsoftware.org/download.php/is.exe
set INNO_INSTALLER=%TEMP%\inno_setup_installer.exe

REM Possible Inno Setup install locations
set INNO_PATH_1=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
set INNO_PATH_2=C:\Program Files\Inno Setup 6\ISCC.exe
set ISCC=

echo.
echo ============================================================
echo   %APP_DISPLAY% v%APP_VERSION% — Windows Build
echo ============================================================
echo.

REM ── Check Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org and re-run.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK]   %PYVER%

REM ── Check / install PyInstaller ───────────────────────────────────────────
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller --quiet
    if errorlevel 1 ( echo [ERROR] Failed to install PyInstaller. & pause & exit /b 1 )
)
for /f "tokens=*" %%v in ('pyinstaller --version 2^>^&1') do set PIVER=%%v
echo [OK]   PyInstaller %PIVER%

REM ── Install / verify Python dependencies ─────────────────────────────────
echo.
echo [INFO] Verifying Python dependencies...
pip install PyQt6 psycopg2-binary python-escpos Pillow python-barcode pyserial pyusb --quiet
if errorlevel 1 ( echo [WARN] Some packages may have failed — build will continue. )
echo [OK]   Python packages ready

REM ── Verify icon exists ────────────────────────────────────────────────────
echo.
if not exist assets\merchant_pos.ico (
    echo [ERROR] assets\merchant_pos.ico not found.
    echo         Make sure the assets\ folder is next to this script.
    pause & exit /b 1
)
echo [OK]   Icon found: assets\merchant_pos.ico

REM ── Check for Inno Setup ──────────────────────────────────────────────────
echo.
if exist "%INNO_PATH_1%" (
    set ISCC=%INNO_PATH_1%
    echo [OK]   Inno Setup found
) else if exist "%INNO_PATH_2%" (
    set ISCC=%INNO_PATH_2%
    echo [OK]   Inno Setup found
) else (
    echo [INFO] Inno Setup not found. Downloading installer...
    powershell -Command "Invoke-WebRequest -Uri '%INNO_URL%' -OutFile '%INNO_INSTALLER%'" 2>nul
    if not exist "%INNO_INSTALLER%" (
        echo [WARN] Could not download Inno Setup. Portable build only.
        echo        Download manually from https://jrsoftware.org/isinfo.php
        set ISCC=
        goto skip_inno_install
    )
    echo [INFO] Installing Inno Setup silently...
    "%INNO_INSTALLER%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
    timeout /t 8 /nobreak >nul
    if exist "%INNO_PATH_1%" (
        set ISCC=%INNO_PATH_1%
        echo [OK]   Inno Setup installed
    ) else if exist "%INNO_PATH_2%" (
        set ISCC=%INNO_PATH_2%
        echo [OK]   Inno Setup installed
    ) else (
        echo [WARN] Inno Setup install may not have completed. Portable build only.
        set ISCC=
    )
)
:skip_inno_install

REM ── Clean previous build ──────────────────────────────────────────────────
echo.
echo [INFO] Cleaning previous build...
if exist build\%APP_NAME%                    rmdir /s /q build\%APP_NAME%
if exist dist\%APP_NAME%                     rmdir /s /q dist\%APP_NAME%
if exist dist\%APP_NAME%_Setup_v%APP_VERSION%.exe  del /q dist\%APP_NAME%_Setup_v%APP_VERSION%.exe
echo [OK]   Clean done

REM ── Run PyInstaller ───────────────────────────────────────────────────────
echo.
echo [INFO] Running PyInstaller (1-3 minutes on first build)...
echo.

pyinstaller merchant_pos.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller failed. Check output above.
    pause & exit /b 1
)

REM ── Post-build: storedata, assets, libusb ────────────────────────────────
echo.
echo [INFO] Post-build setup...

if not exist dist\%APP_NAME%\storedata mkdir dist\%APP_NAME%\storedata
echo [OK]   storedata\ ready

if not exist dist\%APP_NAME%\assets mkdir dist\%APP_NAME%\assets
copy /y assets\merchant_pos.ico     dist\%APP_NAME%\assets\ >nul
copy /y assets\merchant_pos_128.png dist\%APP_NAME%\assets\ >nul 2>nul
copy /y assets\merchant_pos_256.png dist\%APP_NAME%\assets\ >nul 2>nul
copy /y assets\merchant_pos_512.png dist\%APP_NAME%\assets\ >nul 2>nul
echo [OK]   Icons copied to dist\%APP_NAME%\assets\

if exist README.md           copy /y README.md           dist\%APP_NAME%\ >nul
if exist import_stock_dbf.py copy /y import_stock_dbf.py dist\%APP_NAME%\ >nul

REM libusb for USB thermal printers
if exist "C:\Windows\System32\libusb-1.0.dll" (
    copy /y "C:\Windows\System32\libusb-1.0.dll" dist\%APP_NAME%\ >nul
    echo [OK]   libusb-1.0.dll bundled
) else if exist "C:\Windows\SysWOW64\libusb-1.0.dll" (
    copy /y "C:\Windows\SysWOW64\libusb-1.0.dll" dist\%APP_NAME%\ >nul
    echo [OK]   libusb-1.0.dll bundled (SysWOW64^)
) else (
    echo [WARN] libusb-1.0.dll not found. USB thermal printer needs it.
    echo        Get it from https://libusb.info and drop it in dist\%APP_NAME%\
)

REM ── Create Inno Setup installer ───────────────────────────────────────────
echo.
if not defined ISCC goto skip_installer

echo [INFO] Generating Inno Setup script...

for %%i in (dist\%APP_NAME%)           do set PORTABLE_ABS=%%~fi
for %%i in (dist)                       do set DIST_ABS=%%~fi
for %%i in (assets\merchant_pos.ico)    do set ICO_ABS=%%~fi

set ISS_FILE=%TEMP%\merchant_pos_installer.iss

(
echo [Setup]
echo AppName=%APP_DISPLAY%
echo AppVersion=%APP_VERSION%
echo AppVerName=%APP_DISPLAY% v%APP_VERSION%
echo AppPublisher=%APP_PUBLISHER%
echo DefaultDirName={autopf}\%APP_NAME%
echo DefaultGroupName=%APP_DISPLAY%
echo AllowNoIcons=yes
echo OutputDir=%DIST_ABS%
echo OutputBaseFilename=%APP_NAME%_Setup_v%APP_VERSION%
echo SetupIconFile=%ICO_ABS%
echo UninstallDisplayIcon={app}\assets\merchant_pos.ico
echo Compression=lzma2/ultra64
echo SolidCompression=yes
echo WizardStyle=modern
echo MinVersion=10.0
echo PrivilegesRequired=admin
echo DisableProgramGroupPage=no
echo.
echo [Languages]
echo Name: "english"; MessagesFile: "compiler:Default.isl"
echo.
echo [Tasks]
echo Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
echo.
echo [Files]
echo Source: "%PORTABLE_ABS%\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
echo.
echo [Icons]
echo Name: "{group}\%APP_DISPLAY%";            Filename: "{app}\%APP_NAME%.exe"; IconFilename: "{app}\assets\merchant_pos.ico"
echo Name: "{group}\Uninstall %APP_DISPLAY%"; Filename: "{uninstallexe}"
echo Name: "{autodesktop}\%APP_DISPLAY%";      Filename: "{app}\%APP_NAME%.exe"; IconFilename: "{app}\assets\merchant_pos.ico"; Tasks: desktopicon
echo.
echo [Run]
echo Filename: "{app}\%APP_NAME%.exe"; Description: "{cm:LaunchProgram,%APP_DISPLAY%}"; Flags: nowait postinstall skipifsilent
echo.
echo [UninstallDelete]
echo Type: filesandordirs; Name: "{app}\storedata"
) > "%ISS_FILE%"

echo [INFO] Compiling installer...
"%ISCC%" "%ISS_FILE%"
if errorlevel 1 (
    echo [WARN] Inno Setup had errors. Check output above.
) else (
    if exist "dist\%APP_NAME%_Setup_v%APP_VERSION%.exe" (
        echo [OK]   Installer ready: dist\%APP_NAME%_Setup_v%APP_VERSION%.exe
    )
)
del /q "%ISS_FILE%" 2>nul

:skip_installer

REM ── Done ─────────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo   BUILD COMPLETE
echo ============================================================
echo.
echo   Portable:    dist\%APP_NAME%\
echo   Executable:  dist\%APP_NAME%\%APP_NAME%.exe
if exist "dist\%APP_NAME%_Setup_v%APP_VERSION%.exe" (
echo   Installer:   dist\%APP_NAME%_Setup_v%APP_VERSION%.exe
echo.
echo   The installer gives you:
echo     [+] Start Menu shortcut with icon
echo     [+] Optional Desktop shortcut with icon  (tick during install^)
echo     [+] Proper Add/Remove Programs entry
)
echo.
echo ============================================================
echo.

explorer dist\%APP_NAME%
pause
