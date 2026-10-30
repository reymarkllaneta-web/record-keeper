@echo off
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
curl -s -o nul -w "sign-in page HTTP %%{http_code}\n" http://127.0.0.1:8000/accounts/sign-in/ > logs\site_check_log.txt 2>&1
