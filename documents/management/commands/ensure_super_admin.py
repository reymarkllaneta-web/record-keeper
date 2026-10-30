"""Creates the first Super administrator from environment variables, once.

Used on Render, where the free plan has no shell to run create_super_admin.py.
Set these in the Render dashboard (Environment tab):

    SUPERADMIN_USERNAME, SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD

The command runs on every deploy but does nothing when the variables are
missing or the username already exists, so the password is never reset
behind anyone's back. After the first sign-in the variables can be deleted.
"""
import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.core.validators import validate_email
from django.utils import timezone

from accounts.models import User


class Command(BaseCommand):
    help = "Create the first Super administrator from SUPERADMIN_* environment variables."

    def handle(self, *args, **options):
        username = os.getenv("SUPERADMIN_USERNAME", "").strip()
        email = os.getenv("SUPERADMIN_EMAIL", "").strip()
        password = os.getenv("SUPERADMIN_PASSWORD", "")

        if not (username and email and password):
            self.stdout.write("Super administrator: SUPERADMIN_* not set, skipping.")
            return

        if User.objects.filter(username__iexact=username).exists():
            self.stdout.write(f"Super administrator: '{username}' already exists, leaving it as it is.")
            return

        try:
            validate_email(email)
        except ValidationError:
            self.stderr.write("Super administrator: SUPERADMIN_EMAIL is not a valid email, skipping.")
            return

        user = User(
            username=username,
            email=email,
            role=User.Role.SUPERADMIN,
            is_active=True,
            approval_status=User.Approval.APPROVED,
            approved_at=timezone.now(),
        )
        try:
            validate_password(password, user)
        except ValidationError as e:
            self.stderr.write("Super administrator: password too weak - " + " ".join(e.messages))
            return

        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Super administrator '{username}' created."))
