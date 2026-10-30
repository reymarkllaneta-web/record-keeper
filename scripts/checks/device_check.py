"""Shows the brand and model the audit trail will use for this computer."""
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from documents.models import this_computer_model
with open("logs/device_check_log.txt", "w", encoding="utf-8") as out:
    out.write("This computer: " + (this_computer_model() or "(not available)") + "\n")
