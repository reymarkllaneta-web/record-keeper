@echo off
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
".venv\Scripts\python.exe" -u scripts\accounts\list_accounts.py > logs\list_accounts_log.txt 2>&1
