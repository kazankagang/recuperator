@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
start "" "%~dp0recuperator.html"
python -m uvicorn main:app --reload --port 8000
