@echo off
REM Stops any running dev server, checks the database connection, applies migrations, starts the server again.
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
echo Stopping the old server...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*manage.py*runserver*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
call ".venv\Scripts\activate.bat"
(
echo === database ===
python -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup();from django.db import connection as c;c.ensure_connection();print('engine:',c.vendor,'| database:',c.settings_dict['NAME']);from accounts.models import User;print('accounts in this database:',User.objects.count())"
echo === migrate ===
python manage.py migrate
) > logs\restart_log.txt 2>&1
type logs\restart_log.txt
echo.
echo  Open http://127.0.0.1:8000/   (Ctrl+C to stop)
echo.
start "" http://127.0.0.1:8000/
python manage.py runserver
pause
