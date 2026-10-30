"""Makes PostgreSQL's password for DB_USER match DB_PASSWORD in .env.
Asks for the postgres admin password (typed by you, never shown or saved)."""
import getpass, os, sys
import psycopg
from psycopg import sql
from dotenv import load_dotenv

load_dotenv(".env")
e = os.environ
user, pw, db = e.get("DB_USER", ""), e.get("DB_PASSWORD", ""), e.get("DB_NAME", "")
host, port = e.get("DB_HOST", "localhost"), e.get("DB_PORT", "5432")
if not (user and pw and db):
    sys.exit("DB_USER, DB_PASSWORD and DB_NAME must all be set in .env")

print(f"This will set the password of PostgreSQL user '{user}' to the DB_PASSWORD in .env.\n")
for attempt in range(3):
    admin_pw = getpass.getpass("Enter the password for PostgreSQL user 'postgres' (typing is hidden): ")
    try:
        conn = psycopg.connect(dbname="postgres", user="postgres", password=admin_pw,
                               host=host, port=port, autocommit=True, connect_timeout=10)
        break
    except psycopg.OperationalError as ex:
        print("  Could not sign in as postgres:", str(ex).splitlines()[0])
else:
    sys.exit("\nGave up after 3 tries. If you don't know the postgres password, tell Claude.")

exists = conn.execute("select 1 from pg_roles where rolname=%s", (user,)).fetchone()
if exists:
    conn.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(sql.Identifier(user), sql.Literal(pw)))
    print(f"\nPassword for '{user}' updated.")
else:
    conn.execute(sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(sql.Identifier(user), sql.Literal(pw)))
    print(f"\nUser '{user}' did not exist, so it was created.")
dbs = conn.execute("select 1 from pg_database where datname=%s", (db,)).fetchone()
print(f"Database '{db}' exists:", bool(dbs))
conn.close()

try:
    test = psycopg.connect(dbname=db, user=user, password=pw, host=host, port=port, connect_timeout=10)
    n = test.execute("select count(*) from accounts_user").fetchone()[0]
    print(f"Test sign-in as '{user}' worked. Accounts in the database: {n}")
    test.close()
except Exception as ex:
    print("Test sign-in failed:", str(ex).splitlines()[0])
    sys.exit(1)
