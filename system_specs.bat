@echo off
REM Writes this computer's specs and software versions to logs\system_specs.txt (for Chapter III tables).
cd /d "%~dp0"
if not exist logs mkdir logs
set OUT=logs\system_specs.txt
echo === SYSTEMINFO > %OUT%
systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Manufacturer" /C:"System Model" /C:"System Type" /C:"Total Physical Memory" >> %OUT%
echo === CPU >> %OUT%
powershell -NoProfile -Command "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | Format-List" >> %OUT% 2>&1
echo === DISKS >> %OUT%
powershell -NoProfile -Command "Get-CimInstance Win32_DiskDrive | ForEach-Object { $_.Model + ' | ' + $_.MediaType + ' | ' + [math]::Round($_.Size/1GB) + ' GB' }" >> %OUT% 2>&1
powershell -NoProfile -Command "Get-PhysicalDisk | ForEach-Object { $_.FriendlyName + ' | ' + $_.MediaType + ' | ' + [math]::Round($_.Size/1GB) + ' GB' }" >> %OUT% 2>&1
echo === GPU >> %OUT%
powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }" >> %OUT% 2>&1
echo === PYTHON >> %OUT%
".venv\Scripts\python.exe" --version >> %OUT% 2>&1
".venv\Scripts\python.exe" -m pip list >> %OUT% 2>&1
echo === POSTGRES >> %OUT%
if exist "%USERPROFILE%\pgsql\bin\psql.exe" ("%USERPROFILE%\pgsql\bin\psql.exe" --version >> %OUT% 2>&1) else (psql --version >> %OUT% 2>&1)
echo === GIT >> %OUT%
"C:\Program Files\Git\cmd\git.exe" --version >> %OUT% 2>&1
echo === VSCODE >> %OUT%
call code --version >> %OUT% 2>&1
echo === CHROME >> %OUT%
powershell -NoProfile -Command "(Get-Item 'C:\Program Files\Google\Chrome\Application\chrome.exe').VersionInfo.ProductVersion" >> %OUT% 2>&1
echo DONE >> %OUT%
