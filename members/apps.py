from django.apps import AppConfig

from django.apps import AppConfig
import logging

class MembersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "members"

    def ready(self):
        try:
            from . import signals  # noqa: F401
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Klarte ikke å laste members.signals")
