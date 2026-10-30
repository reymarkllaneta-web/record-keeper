@echo off
title Reset database password
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*scripts\database\fix_db_password.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
".venv\Scripts\python.exe" -u scripts\database\reset_db_password.py
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
