@echo off
REM Installs the new packages for online hosting, then runs every test and a deploy check.
REM Results: logs\render_prep.txt
cd /d "%~dp0"
if not exist logs mkdir logs
echo Installing packages and running tests, please wait...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt > logs\render_prep.txt 2>&1
echo PIP EXIT %ERRORLEVEL% >> logs\render_prep.txt
set PYTHONPATH=%CD%;%CD%\scripts\testing
".venv\Scripts\python.exe" -u manage.py test accounts documents test_functions --settings=test_settings --noinput >> logs\render_prep.txt 2>&1
echo TEST EXIT %ERRORLEVEL% >> logs\render_prep.txt
set DJANGO_DEBUG=False
".venv\Scripts\python.exe" manage.py collectstatic --noinput --dry-run >> logs\render_prep.txt 2>&1
echo STATIC EXIT %ERRORLEVEL% >> logs\render_prep.txt
echo DONE >> logs\render_prep.txt
