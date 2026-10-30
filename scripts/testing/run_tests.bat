@echo off
REM Runs every automated test on a throwaway database. Real data, Cloudinary and email are never touched.
REM Results: logs\test_results.txt
cd /d "%~dp0..\.."
if not exist logs mkdir logs
set PYTHONPATH=%CD%;%CD%\scripts\testing
echo Running tests, please wait...
".venv\Scripts\python.exe" -u manage.py test accounts documents test_functions --settings=test_settings -v 2 --noinput > logs\test_results.txt 2>&1
echo EXIT CODE %ERRORLEVEL% >> logs\test_results.txt
