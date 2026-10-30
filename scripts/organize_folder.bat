@echo off
REM One-time tidy: moves helper scripts into scripts\ and logs into logs\. Nothing is deleted.
cd /d "%~dp0.."
if not exist logs mkdir logs
if not exist scripts\database mkdir scripts\database
if not exist scripts\accounts mkdir scripts\accounts
if not exist scripts\checks mkdir scripts\checks
if not exist scripts\setup mkdir scripts\setup
if exist "db_check.bat" move /y "db_check.bat" "scripts\database\" >nul
if exist "verify_database.bat" move /y "verify_database.bat" "scripts\database\" >nul
if exist "start_postgres.bat" move /y "start_postgres.bat" "scripts\database\" >nul
if exist "migrate.bat" move /y "migrate.bat" "scripts\database\" >nul
if exist "list_databases.bat" move /y "list_databases.bat" "scripts\database\" >nul
if exist "list_databases.py" move /y "list_databases.py" "scripts\database\" >nul
if exist "grant_access.bat" move /y "grant_access.bat" "scripts\database\" >nul
if exist "grant_access.py" move /y "grant_access.py" "scripts\database\" >nul
if exist "fix_db_password.bat" move /y "fix_db_password.bat" "scripts\database\" >nul
if exist "fix_db_password.py" move /y "fix_db_password.py" "scripts\database\" >nul
if exist "reset_db_password.bat" move /y "reset_db_password.bat" "scripts\database\" >nul
if exist "reset_db_password.py" move /y "reset_db_password.py" "scripts\database\" >nul
if exist "finish_reset.bat" move /y "finish_reset.bat" "scripts\database\" >nul
if exist "unstick.bat" move /y "unstick.bat" "scripts\database\" >nul
if exist "create_admin.bat" move /y "create_admin.bat" "scripts\accounts\" >nul
if exist "create_admin.py" move /y "create_admin.py" "scripts\accounts\" >nul
if exist "create_super_admin.bat" move /y "create_super_admin.bat" "scripts\accounts\" >nul
if exist "create_super_admin.py" move /y "create_super_admin.py" "scripts\accounts\" >nul
if exist "make_super_admin.bat" move /y "make_super_admin.bat" "scripts\accounts\" >nul
if exist "make_super_admin.py" move /y "make_super_admin.py" "scripts\accounts\" >nul
if exist "list_accounts.bat" move /y "list_accounts.bat" "scripts\accounts\" >nul
if exist "list_accounts.py" move /y "list_accounts.py" "scripts\accounts\" >nul
if exist "seed_demo.bat" move /y "seed_demo.bat" "scripts\accounts\" >nul
if exist "brevo_check.bat" move /y "brevo_check.bat" "scripts\checks\" >nul
if exist "brevo_check.py" move /y "brevo_check.py" "scripts\checks\" >nul
if exist "cloudinary_check.bat" move /y "cloudinary_check.bat" "scripts\checks\" >nul
if exist "cloudinary_check.py" move /y "cloudinary_check.py" "scripts\checks\" >nul
if exist "site_check.bat" move /y "site_check.bat" "scripts\checks\" >nul
if exist "view_check.bat" move /y "view_check.bat" "scripts\checks\" >nul
if exist "view_check.py" move /y "view_check.py" "scripts\checks\" >nul
if exist "add_cloudinary_lines.bat" move /y "add_cloudinary_lines.bat" "scripts\setup\" >nul
if exist "fix_sender.bat" move /y "fix_sender.bat" "scripts\setup\" >nul
if exist "restart_server.bat" move /y "restart_server.bat" "scripts\setup\" >nul
if exist "open_vscode.bat" move /y "open_vscode.bat" "scripts\setup\" >nul
if exist "brevo_check_log.txt" move /y "brevo_check_log.txt" "logs\" >nul
if exist "cloudinary_check_log.txt" move /y "cloudinary_check_log.txt" "logs\" >nul
if exist "db_check_log.txt" move /y "db_check_log.txt" "logs\" >nul
if exist "finish_reset_log.txt" move /y "finish_reset_log.txt" "logs\" >nul
if exist "grant_access_log.txt" move /y "grant_access_log.txt" "logs\" >nul
if exist "list_accounts_log.txt" move /y "list_accounts_log.txt" "logs\" >nul
if exist "list_databases_log.txt" move /y "list_databases_log.txt" "logs\" >nul
if exist "migrate_log.txt" move /y "migrate_log.txt" "logs\" >nul
if exist "postgres_log.txt" move /y "postgres_log.txt" "logs\" >nul
if exist "restart_log.txt" move /y "restart_log.txt" "logs\" >nul
if exist "start_all_log.txt" move /y "start_all_log.txt" "logs\" >nul
if exist "view_check_err.txt" move /y "view_check_err.txt" "logs\" >nul
if exist "view_check_log.txt" move /y "view_check_log.txt" "logs\" >nul
if exist "site_check_log.txt" move /y "site_check_log.txt" "logs\" >nul
dir /b > logs\organize_log.txt
