@echo off
title Fix database password
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
".venv\Scripts\python.exe" -u scripts\database\fix_db_password.py
if errorlevel 1 (
    echo.
    echo Not fixed. See the message above.
    pause
    exit /b 1
)
echo.
echo Restarting the system...
call start_all.bat
echo.
echo Done. Open http://127.0.0.1:8000/ and sign in.
pause
