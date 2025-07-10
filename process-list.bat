@echo off
call venv\Scripts\activate.bat
pip install -r requirements.txt
pip install pyperclip
python main.py
pause