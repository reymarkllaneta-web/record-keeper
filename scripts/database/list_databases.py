"""Lists PostgreSQL databases/roles and which databases contain the archive's accounts table."""
import os, psycopg
port = "5432"
def connect(db):
    return psycopg.connect(dbname=db, user="postgres", host="127.0.0.1", port=port, connect_timeout=8, autocommit=True)
c = connect("postgres")
print("ROLES:", [r[0] for r in c.execute("select rolname from pg_roles where rolname !~ '^pg_' order by 1")])
dbs = [r[0] for r in c.execute("select datname from pg_database where not datistemplate order by 1")]
print("DATABASES:", dbs)
c.close()
for d in dbs:
    try:
        x = connect(d)
        owner = x.execute("select pg_catalog.pg_get_userbyid(datdba) from pg_database where datname=%s", (d,)).fetchone()[0]
        has = x.execute("select to_regclass('public.accounts_user')").fetchone()[0]
        line = f"  {d}: owner={owner}"
        if has:
            n = x.execute("select count(*) from accounts_user").fetchone()[0]
            users = [r[0] for r in x.execute("select username from accounts_user order by id limit 15")]
            docs = x.execute("select to_regclass('public.documents_document')").fetchone()[0]
            nd = x.execute("select count(*) from documents_document").fetchone()[0] if docs else 0
            tbl_owner = x.execute("select tableowner from pg_tables where tablename='accounts_user'").fetchone()[0]
            line += f" | ARCHIVE DB: {n} accounts {users}, {nd} documents, tables owned by {tbl_owner}"
        print(line)
        x.close()
    except Exception as ex:
        print(f"  {d}: could not open ({str(ex).splitlines()[0]})")
