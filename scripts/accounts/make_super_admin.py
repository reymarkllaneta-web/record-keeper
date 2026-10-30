"""Makes 'admin' the Super administrator, sets its email, and sets a new password you type (hidden)."""
import getpass, os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from accounts.models import User

USERNAME, EMAIL = "admin", "reymarkllaneta2218@gmail.com"
u = User.objects.get(username=USERNAME)
u.role = User.Role.SUPERADMIN
u.email = EMAIL
u.is_active = True
u.approval_status = User.Approval.APPROVED
print(f"Account '{USERNAME}' -> Super administrator, email {EMAIL}\n")
while True:
    p1 = getpass.getpass("New password for 'admin' (typing is hidden): ")
    p2 = getpass.getpass("Type it again: ")
    if p1 != p2:
        print("  They didn't match. Try again.\n"); continue
    try:
        validate_password(p1, u)
    except ValidationError as e:
        print("  " + " ".join(e.messages) + "\n"); continue
    break
u.set_password(p1)
u.save()
print("\nDone. Sign in at http://127.0.0.1:8000/ as 'admin' with the new password.")
print(f"A sign-in code will be emailed to {EMAIL}.")
