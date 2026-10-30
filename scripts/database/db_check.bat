@echo off
REM Diagnoses the PostgreSQL connection. Output goes to logs\db_check_log.txt (passwords are never printed).
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
echo === PostgreSQL services === > logs\db_check_log.txt
powershell -NoProfile -Command "Get-Service | Where-Object { $_.Name -like '*postgres*' } | Format-Table -AutoSize Name,Status | Out-String -Width 200" >> logs\db_check_log.txt 2>&1
echo === listening on 5432 === >> logs\db_check_log.txt
netstat -ano | findstr ":5432" >> logs\db_check_log.txt 2>&1
echo === python processes === >> logs\db_check_log.txt
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ForEach-Object { '{0}  {1}' -f $_.ProcessId, $_.CommandLine } | Out-String -Width 300" >> logs\db_check_log.txt 2>&1
echo === connect test, 8s timeout === >> logs\db_check_log.txt
".venv\Scripts\python.exe" -u -c "import os,dotenv,psycopg;dotenv.load_dotenv('.env');e=os.environ;print('host',e.get('DB_HOST'),'port',e.get('DB_PORT'),'db',e.get('DB_NAME'),'user',e.get('DB_USER'));c=psycopg.connect(dbname=e['DB_NAME'],user=e['DB_USER'],password=e.get('DB_PASSWORD',''),host=e.get('DB_HOST','localhost'),port=e.get('DB_PORT','5432'),connect_timeout=8);print('CONNECTED, server version',c.info.server_version);print('accounts_user rows:',c.execute('select count(*) from accounts_user').fetchone()[0])" >> logs\db_check_log.txt 2>&1
echo === done === >> logs\db_check_log.txt
