"""Creates a new Super administrator account. Asks for username, name, email and password (hidden)."""
import getpass, os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
from accounts.models import User


def ask(label, required=True):
    while True:
        value = input(label).strip()
        if value or not required:
            return value
        print("  This is required.\n")


print("Create a new Super administrator\n")

while True:
    username = ask("Username: ")
    if User.objects.filter(username__iexact=username).exists():
        print(f"  '{username}' is already taken. Pick another (or use make_super_admin.bat to promote it).\n")
        continue
    break

first_name = ask("First name: ", required=False)
last_name = ask("Last name: ", required=False)

while True:
    email = ask("Email (sign-in codes are sent here, so it must be real): ")
    try:
        validate_email(email)
    except ValidationError:
        print("  That doesn't look like a valid email.\n"); continue
    break

u = User(
    username=username,
    first_name=first_name,
    last_name=last_name,
    email=email,
    role=User.Role.SUPERADMIN,
    is_active=True,
    approval_status=User.Approval.APPROVED,
    approved_at=timezone.now(),
)

while True:
    p1 = getpass.getpass(f"Password for '{username}' (typing is hidden): ")
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
print(f"\nDone. '{username}' is now a Super administrator.")
print(f"Sign in at http://127.0.0.1:8000/ - a sign-in code will be emailed to {email}.")
