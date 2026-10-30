@echo off
REM Starts the Records Archive Django dev server. First run also sets everything up.
cd /d "%~dp0"

set PY=python
where python >nul 2>nul || set PY=py

if not exist ".venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    %PY% -m venv .venv || goto :fail
)
call ".venv\Scripts\activate.bat" || goto :fail

if not exist ".venv\.deps_installed" (
    echo [setup] Installing requirements...
    python -m pip install --upgrade pip
    echo ok> ".venv\.deps_installed"
)
REM Picks up anything newly added to requirements.txt; quick when nothing changed.
pip install -q -r requirements.txt || goto :fail

if not exist ".env" (
    echo [setup] Creating .env from .env.example...
    copy ".env.example" ".env" >nul
)

set FIRST_RUN=0
if not exist "db.sqlite3" set FIRST_RUN=1

python manage.py makemigrations accounts documents || goto :fail
python manage.py migrate || goto :fail

if "%FIRST_RUN%"=="1" (
    echo [setup] Seeding demo accounts and sample records...
    python manage.py seed_archive
)

echo.
echo  Open http://127.0.0.1:8000/   (Ctrl+C to stop)
echo.
start "" http://127.0.0.1:8000/
python manage.py runserver
pause
exit /b 0

:fail
echo.
echo  Something failed above. Copy the error and send it to Claude.
pause
exit /b 1
