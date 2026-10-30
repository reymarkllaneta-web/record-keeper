import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from accounts.models import User
for u in User.objects.order_by("id"):
    print(f"{u.username:12} role={u.role:6} superuser={u.is_superuser} active={u.is_active} "
          f"approval={u.approval_status} email={u.email or '(none)'} name={u.get_full_name()!r} last_login={u.last_login}")
