"""Gives docarchive_app ownership of the docarchive_db database objects so the website (and migrate) can use them."""
import psycopg
from psycopg import sql
DB, ROLE = "docarchive_db", "docarchive_app"
c = psycopg.connect(dbname=DB, user="postgres", host="127.0.0.1", port="5432", autocommit=True, connect_timeout=8)
c.execute(sql.SQL("ALTER DATABASE {} OWNER TO {}").format(sql.Identifier(DB), sql.Identifier(ROLE)))
c.execute(sql.SQL("ALTER SCHEMA public OWNER TO {}").format(sql.Identifier(ROLE)))
n = 0
for (t,) in c.execute("select tablename from pg_tables where schemaname='public'").fetchall():
    c.execute(sql.SQL("ALTER TABLE public.{} OWNER TO {}").format(sql.Identifier(t), sql.Identifier(ROLE))); n += 1
s = 0
for (q,) in c.execute("select sequence_name from information_schema.sequences where sequence_schema='public'").fetchall():
    c.execute(sql.SQL("ALTER SEQUENCE public.{} OWNER TO {}").format(sql.Identifier(q), sql.Identifier(ROLE))); s += 1
v = 0
for (w,) in c.execute("select viewname from pg_views where schemaname='public'").fetchall():
    c.execute(sql.SQL("ALTER VIEW public.{} OWNER TO {}").format(sql.Identifier(w), sql.Identifier(ROLE))); v += 1
print(f"OK: {ROLE} now owns database {DB}, schema public, {n} tables, {s} sequences, {v} views")
c.close()
