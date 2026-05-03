"""
main.py
Entry point for the POS system.
Run this file to start the application: python main.py
"""
import sys
import os

# Make sure Python can find all project modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from config import APP_NAME, APP_VERSION
from db import create_tables


def main():
    # ----------------------------------------------------------------
    # Step 1 — Start the PyQt6 application
    # ----------------------------------------------------------------
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # ----------------------------------------------------------------
    # Step 2 — Apply theme (dark only)
    # ----------------------------------------------------------------
    from ui.theme import ThemeManager
    ThemeManager.instance().apply(app)

    # ----------------------------------------------------------------
    # Step 3 — Initialise databases (safe to run every time)
    # ----------------------------------------------------------------
    create_tables()

    # ----------------------------------------------------------------
    # Step 4 — First-run check
    # If no users exist show the setup wizard; otherwise show login
    # ----------------------------------------------------------------
    from ui.setup_wizard import is_first_run, SetupWizard
    from ui.login_window import LoginWindow

    if is_first_run():
        window = SetupWizard(app)
    else:
        window = LoginWindow(app)

    window.show()

    # ----------------------------------------------------------------
    # Step 5 — Run the event loop
    # ----------------------------------------------------------------
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
