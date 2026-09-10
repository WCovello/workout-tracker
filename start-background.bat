@echo off
:: Workout Tracker — background launcher
:: This starts the app silently with no terminal window.
:: Place a shortcut to this file in your Windows Startup folder
:: to have it run automatically on login.

cd /d "%~dp0"
call venv\Scripts\activate.bat
start "" pythonw launcher.py
