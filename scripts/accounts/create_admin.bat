@echo off
title Create admin
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
".venv\Scripts\python.exe" -u scripts\accounts\create_admin.py
echo.
pause
