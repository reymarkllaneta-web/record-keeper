@echo off
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='powershell.exe'\" | Where-Object { $_.CommandLine -like '*pg_ctl*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
