@echo off
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
".venv\Scripts\python.exe" -u scripts\checks\device_check.py > logs\device_check_err.txt 2>&1
