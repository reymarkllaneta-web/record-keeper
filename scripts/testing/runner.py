"""Test runner that keeps every test offline and off the real file store."""
import requests
from django.apps import apps
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import FileField
from django.test.runner import DiscoverRunner


def _no_network(self, method, url, *args, **kwargs):
    raise requests.exceptions.ConnectionError(f"Network is switched off during tests ({url})")


class OfflineRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        # Model file fields point at Cloudinary storage objects directly; send
        # them to a temporary folder instead.
        local = FileSystemStorage(location=settings.MEDIA_ROOT)
        for model in apps.get_models():
            for field in model._meta.get_fields():
                if isinstance(field, FileField):
                    field.storage = local
        # Nothing may reach Cloudinary or Brevo.
        self._real_request = requests.Session.request
        requests.Session.request = _no_network

    def teardown_test_environment(self, **kwargs):
        requests.Session.request = self._real_request
        super().teardown_test_environment(**kwargs)
