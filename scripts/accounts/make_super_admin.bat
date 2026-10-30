@echo off
title Make super admin
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
".venv\Scripts\python.exe" -u scripts\accounts\make_super_admin.py
echo.
pause
