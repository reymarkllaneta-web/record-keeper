@echo off
REM Adds the demo accounts (admin / clerk) and sample records. Safe to run more than once.
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
call ".venv\Scripts\activate.bat"
python manage.py seed_archive
pause
