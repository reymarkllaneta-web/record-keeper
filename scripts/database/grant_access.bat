@echo off
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
".venv\Scripts\python.exe" -u scripts\database\grant_access.py > logs\grant_access_log.txt 2>&1
powershell -NoProfile -Command "$p='.env'; $t=[IO.File]::ReadAllText($p); $t=$t -replace '(?m)^DB_NAME=docarchive\r?$', ('DB_NAME=docarchive_db' + [char]13); [IO.File]::WriteAllText($p,$t)"
findstr /b "DB_NAME=" .env >> logs\grant_access_log.txt
