#!/bin/sh
# Builds dist/make-ps3-font (one file, with a window) with PyInstaller. Needs Python 3.9+ with tkinter
# (Debian/Ubuntu: apt install python3-venv python3-tk libpython3-dev). Build on the oldest system you want it to run on.
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt pyinstaller
.venv/bin/pyinstaller --noconfirm --onefile --windowed --name make-ps3-font make_ps3_font.py
echo "Built dist/make-ps3-font"
