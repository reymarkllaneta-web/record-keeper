"""Reset PostgreSQL passwords when the 'postgres' password is forgotten.

1. Backs up pg_hba.conf and temporarily allows password-less connections from this computer only.
2. Sets DB_USER's password to the DB_PASSWORD in .env (so the website can connect).
3. Optionally sets a NEW password for 'postgres' (typed by you, hidden, never saved here).
4. Always restores the original pg_hba.conf, even if something fails.
"""
import getpass, os, shutil, subprocess, sys
from pathlib import Path
import psycopg
from psycopg import sql
from dotenv import load_dotenv

load_dotenv(".env")
e = os.environ
user, pw, db = e.get("DB_USER", ""), e.get("DB_PASSWORD", ""), e.get("DB_NAME", "")
if not (user and pw and db):
    sys.exit("DB_USER, DB_PASSWORD and DB_NAME must be set in .env")

pgdir = Path(os.environ["USERPROFILE"]) / "pgsql"
data = pgdir / "data"
hba = data / "pg_hba.conf"
backup = data / "pg_hba.conf.before_reset"
pg_ctl = str(pgdir / "bin" / "pg_ctl.exe")

def reload():
    r = subprocess.run([pg_ctl, "reload", "-D", str(data)], capture_output=True, text=True)
    print("  reload:", (r.stdout or r.stderr).strip())

if not hba.exists():
    sys.exit(f"Could not find {hba}")

original = hba.read_text(encoding="utf-8")
shutil.copy2(hba, backup)
print(f"Backed up pg_hba.conf -> {backup.name}")

temp_rules = ("# TEMPORARY (reset_db_password.py) - restored automatically\n"
              "host all all 127.0.0.1/32 trust\nhost all all ::1/128 trust\n")
ok = False
try:
    hba.write_text(temp_rules + original, encoding="utf-8")
    print("Temporarily allowing local connections without a password...")
    reload()

    conn = psycopg.connect(dbname="postgres", user="postgres", host="127.0.0.1", port=e.get("DB_PORT", "5432"),
                           autocommit=True, connect_timeout=10)
    if conn.execute("select 1 from pg_roles where rolname=%s", (user,)).fetchone():
        conn.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(sql.Identifier(user), sql.Literal(pw)))
        print(f"\n[OK] '{user}' password now matches DB_PASSWORD in .env")
    else:
        conn.execute(sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(sql.Identifier(user), sql.Literal(pw)))
        print(f"\n[OK] '{user}' did not exist - created it with the .env password")

    print("\nOptional: set a NEW password for the 'postgres' admin user (used by pgAdmin).")
    while True:
        new1 = getpass.getpass("  New postgres password (press Enter to skip): ")
        if not new1:
            print("  Skipped - postgres password unchanged.")
            break
        new2 = getpass.getpass("  Type it again: ")
        if new1 == new2:
            conn.execute(sql.SQL("ALTER ROLE postgres WITH PASSWORD {}").format(sql.Literal(new1)))
            print("  [OK] postgres password changed. Write it down somewhere safe.")
            break
        print("  They didn't match, try again.")
    conn.close()
    ok = True
finally:
    hba.write_text(original, encoding="utf-8")
    print("\nRestored the original pg_hba.conf (passwords required again).")
    reload()

if ok:
    try:
        t = psycopg.connect(dbname=db, user=user, password=pw, host="localhost",
                            port=e.get("DB_PORT", "5432"), connect_timeout=10)
        n = t.execute("select count(*) from accounts_user").fetchone()[0]
        print(f"\n[OK] Website can connect. Accounts in '{db}': {n}")
        t.close()
    except Exception as ex:
        print("\nTest connection failed:", str(ex).splitlines()[0])
        sys.exit(1)
else:
    sys.exit(1)
