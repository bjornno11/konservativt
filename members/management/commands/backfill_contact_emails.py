from django.core.management.base import BaseCommand
from django.db.models import Q
from django.conf import settings

class Command(BaseCommand):
    help = "Set contact emails where missing: Fylke.contact_email, Fylkeslag.epost, Lokallag.contact_email/epost"

    def handle(self, *args, **opts):
        from geo.models import Fylke
        from members.models import Fylkeslag, Lokallag

        default = getattr(settings, "DEFAULT_FROM_EMAIL", "bn@zc.no")

        f1 = Fylke.objects.filter(Q(contact_email__isnull=True) | Q(contact_email="")).update(contact_email=default)

        # Fylkeslag bruker 'epost' hos deg
        f2 = Fylkeslag.objects.filter(Q(epost__isnull=True) | Q(epost="")).update(epost=default)

        # Lokallag: støtt begge varianter
        updated_lokallag = 0
        if hasattr(Lokallag, "contact_email"):
            updated_lokallag += Lokallag.objects.filter(Q(contact_email__isnull=True) | Q(contact_email="")).update(contact_email=default)
        if hasattr(Lokallag, "epost"):
            updated_lokallag += Lokallag.objects.filter(Q(epost__isnull=True) | Q(epost="")).update(epost=default)

        self.stdout.write(self.style.SUCCESS(
            f"Updated -> Fylke.contact_email={f1}, Fylkeslag.epost={f2}, Lokallag(any)={updated_lokallag} (default={default})"
        ))
