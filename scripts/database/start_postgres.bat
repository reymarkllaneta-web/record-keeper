@echo off
REM Starts the portable PostgreSQL in C:\Users\Romalyn\pgsql, then unsticks any migrate that was waiting on it.
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
set PGDIR=%USERPROFILE%\pgsql
echo === starting PostgreSQL === > logs\postgres_log.txt
if not exist "%PGDIR%\data\PG_VERSION" (
    echo No initialized data folder at %PGDIR%\data >> logs\postgres_log.txt
    goto :end
)
"%PGDIR%\bin\pg_ctl.exe" status -D "%PGDIR%\data" >> logs\postgres_log.txt 2>&1
"%PGDIR%\bin\pg_ctl.exe" start -D "%PGDIR%\data" -l "%PGDIR%\data\server_log.txt" -w -t 30 >> logs\postgres_log.txt 2>&1
echo === status after start === >> logs\postgres_log.txt
"%PGDIR%\bin\pg_ctl.exe" status -D "%PGDIR%\data" >> logs\postgres_log.txt 2>&1
netstat -ano | findstr ":5432" >> logs\postgres_log.txt 2>&1
echo === last lines of PostgreSQL server log === >> logs\postgres_log.txt
powershell -NoProfile -Command "if (Test-Path \"$env:USERPROFILE\pgsql\data\server_log.txt\") { Get-Content \"$env:USERPROFILE\pgsql\data\server_log.txt\" -Tail 15 }" >> logs\postgres_log.txt 2>&1
echo === stopping stuck migrate processes === >> logs\postgres_log.txt
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*manage.py*migrate*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; 'stopped ' + $_.ProcessId }" >> logs\postgres_log.txt 2>&1
:end
echo === done === >> logs\postgres_log.txt
