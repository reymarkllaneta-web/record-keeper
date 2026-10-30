@echo off
cd /d "%~dp0..\.."
set PYTHONPATH=%CD%
if not exist logs mkdir logs
findstr /b "CLOUDINARY_CLOUD_NAME=" .env >nul 2>&1 && goto :done
>> .env echo.
>> .env echo # Cloudinary (https://console.cloudinary.com) stores scanned documents, attachments and avatars.
>> .env echo # Copy these three values from your Cloudinary dashboard: Settings, API Keys.
>> .env echo CLOUDINARY_CLOUD_NAME=
>> .env echo CLOUDINARY_API_KEY=
>> .env echo CLOUDINARY_API_SECRET=
:done
code .env
