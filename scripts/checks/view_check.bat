@echo off
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
call ".venv\Scripts\activate.bat"
python scripts\checks\view_check.py > logs\view_check_err.txt 2>&1
