# members/apps.py
from django.apps import AppConfig
import logging

# members/apps.py
class MembersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "members"

    def ready(self):
        # Vi sender e-post direkte fra viewet etter commit.
        # (Kan reaktivere signals senere når rotårsaken er funnet.)
        pass
