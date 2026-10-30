"""Checks whether uploaded document files can be fetched for the viewer. Writes view_check_log.txt."""
import os, sys, traceback
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
import requests
from documents.models import Document
from documents import views

out = open("logs/view_check_log.txt", "w", encoding="utf-8")
def p(*a):
    print(*a, file=out, flush=True)

try:
    import mammoth
    p("mammoth:", mammoth.__file__)
except Exception as e:
    p("mammoth: NOT importable:", e)
p("views has _preview_html:", hasattr(views, "_preview_html"))

docs = Document.objects.exclude(file="").exclude(file__isnull=True).order_by("-pk")[:6]
p("documents with files:", Document.objects.exclude(file="").exclude(file__isnull=True).count())
for d in docs:
    p("\n#", d.pk, d.control_number, "|", d.file.name)
    try:
        url = d.file.url
        p("  url:", url)
        r = requests.get(url, timeout=30)
        p("  GET status:", r.status_code, "| bytes:", len(r.content), "| type:", r.headers.get("content-type"))
        if r.status_code != 200:
            p("  body:", r.text[:300].replace("\n", " "))
    except Exception:
        p("  url/GET error:", traceback.format_exc(limit=2))
    try:
        f = views._open_stored_file(d.file)
        if f is None:
            p("  _open_stored_file: None (file could not be opened)")
        else:
            data = f.read()
            p("  _open_stored_file: OK,", len(data), "bytes, starts with", data[:8])
            f.close()
    except Exception:
        p("  _open_stored_file error:", traceback.format_exc(limit=3))
    p("  preview kind:", views._preview_kind(d.file.name))
out.close()
