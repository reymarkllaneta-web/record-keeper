@echo off
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
set PGDATA=%USERPROFILE%\pgsql\data
echo === closing the waiting reset window === > logs\finish_reset_log.txt
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*scripts\database\reset_db_password.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; 'stopped ' + $_.ProcessId }" >> logs\finish_reset_log.txt 2>&1
echo === restoring pg_hba.conf === >> logs\finish_reset_log.txt
if exist "%PGDATA%\pg_hba.conf.before_reset" (
    copy /y "%PGDATA%\pg_hba.conf.before_reset" "%PGDATA%\pg_hba.conf" >> logs\finish_reset_log.txt 2>&1
    "%USERPROFILE%\pgsql\bin\pg_ctl.exe" reload -D "%PGDATA%" >> logs\finish_reset_log.txt 2>&1
)
findstr /c:"TEMPORARY" "%PGDATA%\pg_hba.conf" >nul && (echo STILL TEMPORARY >> logs\finish_reset_log.txt) || (echo restored OK >> logs\finish_reset_log.txt)
call start_all.bat
