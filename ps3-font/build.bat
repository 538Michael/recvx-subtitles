@echo off
rem Builds dist\make-ps3-font.exe (one file, with a window) with PyInstaller. Needs Python 3.9+ with tkinter.
cd /d "%~dp0"
python -m venv .venv || exit /b 1
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt pyinstaller || exit /b 1
.venv\Scripts\pyinstaller --noconfirm --onefile --windowed --name make-ps3-font make_ps3_font.py || exit /b 1
echo Built dist\make-ps3-font.exe
