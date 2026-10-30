@echo off
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
".venv\Scripts\python.exe" -u scripts\checks\cloudinary_check.py > logs\cloudinary_check_log.txt 2>&1
