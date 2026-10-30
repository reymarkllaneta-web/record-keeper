@echo off
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
".venv\Scripts\python.exe" -u scripts\checks\brevo_check.py > logs\brevo_check_log.txt 2>&1
