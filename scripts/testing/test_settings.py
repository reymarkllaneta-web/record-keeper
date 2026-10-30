"""Settings used only while the automated tests run.

Everything that could touch real data is swapped out: a throwaway in-memory
database instead of PostgreSQL, a temporary folder instead of Cloudinary, and
no email service. The real .env and database are never written to.
"""
import tempfile

from config.settings import *  # noqa: F401,F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

MEDIA_ROOT = tempfile.mkdtemp(prefix="archive-test-media-")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
CLOUDINARY_STORAGE = {"CLOUD_NAME": "offline-test", "API_KEY": "0", "API_SECRET": "offline"}

BREVO_API_KEY = ""
BREVO_SENDER_EMAIL = ""

TEST_RUNNER = "runner.OfflineRunner"
