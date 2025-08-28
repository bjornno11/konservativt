from django.apps import AppConfig


class DocsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'docs'

class PeopleConfig(AppConfig):
    name = "people"
    verbose_name = "Medlemsarkiv"
