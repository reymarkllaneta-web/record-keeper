"""Give the next number in their series to records saved with No. 0.

Before the form refused it, typing 0 saved a record that showed as "No. —".
Each such record now takes the next free number of its own type and series
year, in the order the records were filed. Records in the Recycle Bin count
too, because their control numbers stay taken.
"""
from django.db import migrations
from django.db.models import Max, Q


def number_them(apps, schema_editor):
    Document = apps.get_model("documents", "Document")
    blank = Q(number=0) | Q(number__isnull=True)
    for doc in Document.objects.filter(blank).order_by("created_at", "pk"):
        last = (
            Document.objects.filter(doc_type=doc.doc_type, series_year=doc.series_year)
            .exclude(blank)
            .aggregate(Max("number"))["number__max"]
        )
        doc.number = (last or 0) + 1
        doc.save(update_fields=["number"])


class Migration(migrations.Migration):
    dependencies = [("documents", "0013_documentfolder_is_hidden")]
    operations = [migrations.RunPython(number_them, migrations.RunPython.noop)]
