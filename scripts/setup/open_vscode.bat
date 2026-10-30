@echo off
REM Opens this project in VS Code.
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
code . .env
