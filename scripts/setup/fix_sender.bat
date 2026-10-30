@echo off
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
powershell -NoProfile -Command "$p='.env'; $t=[IO.File]::ReadAllText($p); $t=$t.Replace('BREVO_SENDER_EMAIL=reymarklianeta0614@gmail.com','BREVO_SENDER_EMAIL=reymarkllaneta0614@gmail.com'); [IO.File]::WriteAllText($p,$t)"
".venv\Scripts\python.exe" -u scripts\setup\brevo_check.py > logs\brevo_check_log.txt 2>&1
call start_all.bat
