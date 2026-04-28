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
    # sys.argv passes any command line arguments to Qt (required)
    # ----------------------------------------------------------------
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # ----------------------------------------------------------------
    # Step 2 — Make sure the database and all tables are ready
    # Safe to run every time — won't wipe existing data
    # ----------------------------------------------------------------
    create_tables()

    # ----------------------------------------------------------------
    # Step 3 — Show the login window
    # Imported here to avoid circular imports at the top of the file
    # ----------------------------------------------------------------
    from ui.login_window import LoginWindow
    login = LoginWindow()
    login.show()

    # ----------------------------------------------------------------
    # Step 4 — Keep the app running until the window is closed
    # sys.exit ensures a clean exit code when the app closes
    # ----------------------------------------------------------------
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
