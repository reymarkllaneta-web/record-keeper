import os
import re

from django import forms
from django.contrib.auth import password_validation
from django.core.cache import cache
from django.contrib.auth.forms import AdminPasswordChangeForm, AuthenticationForm, UserCreationForm

from .models import Office, User

AVATAR_MAX_SIZE = 2 * 1024 * 1024

# Sign-in lockout: after this many wrong passwords for one username, that
# username is refused for LOGIN_LOCK_MINUTES, counted from the last wrong try.
LOGIN_MAX_FAILURES = 5
LOGIN_LOCK_MINUTES = 15


def _failure_key(username):
    return f"login-failures:{(username or '').strip().lower()}"
AVATAR_ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]


class PHContactNumberField(forms.CharField):
    """A Philippine contact number, normalized to +63XXXXXXXXXX (leading 0 dropped).

    A number is 11 digits written as 0917 123 4567, or 12 with the 63 country
    code. Anything longer is refused outright rather than quietly truncated —
    a wrong number on a record is worse than an empty one.
    """

    # The longest text a valid entry can be: "+63 917 123 4567"
    MAX_INPUT_LENGTH = 17

    default_error_messages = {
        "invalid": "Enter a valid Philippine number, e.g. 0917 123 4567.",
        "too_long": (
            "That is too long. A Philippine number has 11 digits (0917 123 4567), "
            "or 12 with the 63 country code."
        ),
        "too_short": (
            "That is too short. A Philippine number has 11 digits (0917 123 4567), "
            "or 12 with the 63 country code."
        ),
    }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("max_length", self.MAX_INPUT_LENGTH)
        kwargs.setdefault(
            "widget",
            forms.TextInput(attrs={
                "placeholder": "+63 9XX XXX XXXX",
                "inputmode": "tel",
                "autocomplete": "tel",
                "maxlength": self.MAX_INPUT_LENGTH,
                "data-ph-contact": "",
            }),
        )
        kwargs.setdefault("help_text", "Enter as 0917 123 4567 — stored as +63 917 123 4567.")
        super().__init__(*args, **kwargs)

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return value

        digits = re.sub(r"\D", "", value)
        # how many digits this spelling is allowed, counted before the prefix goes
        if digits.startswith("63"):
            allowed, body = 12, digits[2:]
        elif digits.startswith("0"):
            allowed, body = 11, digits[1:]
        else:
            allowed, body = 10, digits

        if len(digits) > allowed:
            raise forms.ValidationError(self.error_messages["too_long"], code="too_long")
        if len(body) < 10:
            raise forms.ValidationError(self.error_messages["too_short"], code="too_short")
        if len(body) != 10 or not body.startswith("9"):
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")
        return f"+63{body}"


class ArchiveLoginForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "inactive": "This account has been disabled. Contact a records administrator to have it reactivated.",
        "pending": "This account is waiting for approval by a super administrator. You will be able to sign in once it is approved.",
        "locked": f"Too many wrong passwords. Sign-in for this account is paused for {LOGIN_LOCK_MINUTES} minutes; "
                  "please try again later or use Forgot your password.",
    }

    username = forms.CharField(
        widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "Username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )

    account_disabled = False
    awaiting_approval = False
    locked_out = False

    def clean(self):
        username = self.cleaned_data.get("username")
        key = _failure_key(username)
        failures = cache.get(key, 0) if username else 0
        if failures >= LOGIN_MAX_FAILURES:
            # Refused before the password is even checked, so guessing gets nowhere.
            self.locked_out = True
            raise forms.ValidationError(self.error_messages["locked"], code="locked")
        try:
            cleaned = super().clean()
        except forms.ValidationError:
            # Only reveal the disabled state to someone who knows the password,
            # so the form can't be used to probe which accounts exist.
            password = self.cleaned_data.get("password")
            user = User.objects.filter(username=username).first() if username else None
            if user and not user.is_active and password and user.check_password(password):
                if user.is_awaiting_approval:
                    self.awaiting_approval = True
                    raise forms.ValidationError(self.error_messages["pending"], code="pending")
                self.account_disabled = True
                raise forms.ValidationError(self.error_messages["inactive"], code="inactive")
            # A wrong password: count it. The same rule applies to names that do
            # not exist, so the lockout reveals nothing about who has an account.
            if username:
                cache.set(key, failures + 1, LOGIN_LOCK_MINUTES * 60)
            raise
        cache.delete(key)
        return cleaned


class UserCreateForm(UserCreationForm):
    contact_number = PHContactNumberField()

    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "email",
            "role", "office", "position", "contact_number",
        ]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Another account already uses this email address.")
        return email


class SignUpForm(UserCreationForm):
    """Public self-registration. The account is created locked, pending approval."""

    contact_number = PHContactNumberField()
    requested_role = forms.ChoiceField(
        label="Role you need",
        choices=[(User.Role.USER, "Staff user — search and read records"),
                 (User.Role.ADMIN, "Administrator — file and manage records")],
        initial=User.Role.USER,
        help_text="A super administrator reviews this and sets your actual role.",
    )
    # Typed in rather than picked from a list; matched to an existing office on save.
    office_name = forms.CharField(
        label="Office or division", max_length=120,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Office of the Mayor"}),
    )

    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "email",
            "position", "contact_number",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("first_name", "last_name", "email"):
            self.fields[name].required = True
        # Autofocus scrolls the panel past its heading, and the stock password
        # rules print as a four-item list that dwarfs the form.
        self.fields["username"].widget.attrs.pop("autofocus", None)
        self.fields["username"].help_text = "Letters, digits and @ . + - _ only."
        self.fields["password1"].help_text = "At least 8 characters, not all numbers, and not a common password."
        self.fields["password2"].help_text = "Type it once more."

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Another account already uses this email address.")
        return email

    def clean_office_name(self):
        name = " ".join(self.cleaned_data.get("office_name", "").split())
        if not name:
            raise forms.ValidationError("Type the office or division you belong to.")
        return name

    def save(self, commit=True):
        user = super().save(commit=False)
        # Link to the office of that name (ignoring capitals), or open it if it is new.
        name = self.cleaned_data["office_name"]
        user.office = (Office.objects.filter(name__iexact=name).first()
                       or Office.objects.create(name=name))
        # Always created as a staff user: the request is only a request.
        user.role = User.Role.USER
        user.requested_role = self.cleaned_data.get("requested_role", User.Role.USER)
        user.approval_status = User.Approval.PENDING
        user.is_active = False          # cannot sign in until approved
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """A user editing their own details. No role, office assignment, or active-state control here."""

    contact_number = PHContactNumberField()

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "contact_number", "avatar"]

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already uses this email address.")
        return email

    def clean_avatar(self):
        upload = self.cleaned_data.get("avatar")
        if not upload or not hasattr(upload, "size"):
            return upload
        if upload.size > AVATAR_MAX_SIZE:
            limit = AVATAR_MAX_SIZE // (1024 * 1024)
            raise forms.ValidationError(f"That image is larger than the {limit} MB limit.")
        ext = os.path.splitext(upload.name)[1].lower()
        if ext not in AVATAR_ALLOWED_EXTENSIONS:
            allowed = ", ".join(AVATAR_ALLOWED_EXTENSIONS)
            raise forms.ValidationError(f"Upload one of these image types: {allowed}.")
        return upload


class AdminSetPasswordForm(AdminPasswordChangeForm):
    """Admin resetting someone else's password, with an opt-in escape from the strength rules."""

    bypass_validation = forms.BooleanField(
        required=False,
        label="Bypass password requirements",
        help_text="Allows a short or simple temporary password. Tell the user to change it after signing in.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django's "unusable password" option is meant for its own admin site and
        # renders its help text as raw markup here; this app always sets a password.
        self.fields.pop("usable_password", None)

    def clean(self):
        if self.cleaned_data.get("bypass_validation"):
            # Keep the "both entries match" check; skip only the strength rules.
            self.validate_passwords()
            return self.cleaned_data
        return super().clean()


class UserUpdateForm(forms.ModelForm):
    contact_number = PHContactNumberField()

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "email",
            "role", "office", "position", "contact_number", "is_active",
        ]

    def __init__(self, *args, editing_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editing_user = editing_user
        # An administrator must not be able to promote anyone to super administrator.
        if editing_user is not None and not editing_user.is_super_admin:
            self.fields["role"].choices = [
                (value, label) for value, label in self.fields["role"].choices
                if value != User.Role.SUPERADMIN
            ]

    def clean(self):
        cleaned = super().clean()
        # An administrator cannot demote or deactivate their own account and
        # lock themselves out of user management.
        if self.editing_user and self.instance.pk == self.editing_user.pk:
            own_role = User.Role.SUPERADMIN if self.editing_user.is_super_admin else User.Role.ADMIN
            if cleaned.get("role") != own_role:
                self.add_error("role", "You cannot change your own role.")
            if not cleaned.get("is_active"):
                self.add_error("is_active", "You cannot deactivate your own account.")
        return cleaned


class OfficeForm(forms.ModelForm):
    class Meta:
        model = Office
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Human Resource Division"}),
            "description": forms.TextInput(attrs={"placeholder": "What this office handles (optional)"}),
        }


class OfficeNotifyForm(forms.Form):
    """Message sent to everyone in one office."""

    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "What should this office be told?"}),
        max_length=240,
    )
    def clean_message(self):
        return self.cleaned_data["message"].strip()


class UserMessageForm(forms.Form):
    """A note sent to one account — e.g. that a filed document needs a correction.

    The document is a reference, never an upload: the record is already on file,
    so the message points at it instead of asking for the file again.
    """

    subject = forms.CharField(
        label="Subject", max_length=120,
        widget=forms.TextInput(attrs={"placeholder": "What is this about?"}),
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            "rows": 5,
            "placeholder": "What should they do or know? e.g. the date on page 2 needs correcting.",
        }),
        max_length=1000,
    )
    document = forms.ModelChoiceField(
        label="About this document", required=False, queryset=None,
        empty_label="Not about a particular document",
        help_text="Links the message to a record already on file. Nothing is uploaded.",
    )

    def __init__(self, *args, documents=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["document"].queryset = documents

    def clean_subject(self):
        return self.cleaned_data["subject"].strip()

    def clean_message(self):
        return self.cleaned_data["message"].strip()


class SecondFactorForm(forms.Form):
    """The 6-digit code from the super administrator's authenticator app."""

    code = forms.CharField(
        label="Authentication code",
        max_length=7,
        widget=forms.TextInput(attrs={
            "autofocus": True, "inputmode": "numeric", "autocomplete": "one-time-code",
            "placeholder": "123456",
        }),
    )

    def clean_code(self):
        return self.cleaned_data["code"].strip().replace(" ", "")


class ForgotPasswordForm(forms.Form):
    """Step one: who are you? Answered the same way whether or not the account exists."""

    identifier = forms.CharField(
        label="Username or email address",
        widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "e.g. clerk3 or you@example.com"}),
    )

    def clean_identifier(self):
        return self.cleaned_data["identifier"].strip()


class ResetPasswordForm(forms.Form):
    """Step two: the emailed code plus the new password."""

    code = forms.CharField(
        label="Code from your email",
        max_length=7,
        widget=forms.TextInput(attrs={"autofocus": True, "inputmode": "numeric",
                                      "autocomplete": "one-time-code", "placeholder": "123456"}),
    )
    new_password1 = forms.CharField(label="New password", strip=False, widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="Confirm new password", strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["new_password1"].help_text = (
            "At least 8 characters, not all numbers, and not a common password."
        )

    def clean_code(self):
        return self.cleaned_data["code"].strip().replace(" ", "")

    def clean(self):
        cleaned = super().clean()
        first, second = cleaned.get("new_password1"), cleaned.get("new_password2")
        if first and second and first != second:
            self.add_error("new_password2", "The two passwords do not match.")
        elif first:
            try:
                password_validation.validate_password(first, self.user)
            except forms.ValidationError as exc:
                self.add_error("new_password1", exc)
        return cleaned
