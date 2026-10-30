@echo off
REM Uploads the project to GitHub (passwords in .env, the database and .venv are NOT uploaded).
cd /d "%~dp0"
if not exist logs mkdir logs
where git >nul 2>nul || set "PATH=%PATH%;C:\Program Files\Git\cmd"
if not exist ".git" git init -b main
for /f "delims=" %%e in ('git config user.email') do set GITMAIL=%%e
if not defined GITMAIL git config user.email "recordkeeper@users.noreply.github.com"
if not defined GITMAIL git config user.name "Record Keeper"
git add -A
echo.
echo Files that will be uploaded:
git status --short > logs\git_files.txt
type logs\git_files.txt | find /c /v ""
git commit -q -m "Record Keeper: ready for Render"
git branch -M main
git remote remove origin 2>nul
git remote add origin https://github.com/reymarkllaneta-web/record-keeper.git
echo.
echo Uploading to GitHub. If a GitHub sign-in window opens, sign in there.
git push -u origin main
echo PUSH EXIT %ERRORLEVEL% > logs\git_push.txt
echo.
echo Finished. You can close this window.
pause
