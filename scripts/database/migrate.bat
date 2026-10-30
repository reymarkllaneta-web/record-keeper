@echo off
REM Creates any new migrations and applies them. Output is also saved to logs\migrate_log.txt.
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
call ".venv\Scripts\activate.bat"
(
echo === makemigrations ===
python manage.py makemigrations
echo === migrate ===
python manage.py migrate
) > logs\migrate_log.txt 2>&1
type logs\migrate_log.txt
pause
