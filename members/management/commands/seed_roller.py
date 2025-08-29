# members/management/commands/seed_roller.py
from django.core.management.base import BaseCommand
from members.models import Rolle

DEFAULTS = [
    ("leder", "Leder", "sentral", 1),
    ("nestleder", "Nestleder", "sentral", 2),
    ("styremedlem", "Styremedlem", "sentral", 10),

    ("fylkesleder", "Fylkesleder", "fylke", 1),
    ("fylkesstyremedlem", "Styremedlem fylkeslag", "fylke", 10),

    ("lokalleder", "Leder lokallag", "lokal", 1),
    ("lokalstyremedlem", "Styremedlem lokallag", "lokal", 10),
]

class Command(BaseCommand):
    help = "Opprett standard roller for alle nivå"

    def handle(self, *args, **kwargs):
        created = 0
        for kode, navn, scope, rang in DEFAULTS:
            obj, was_created = Rolle.objects.get_or_create(
                kode=kode, scope=scope,
                defaults={"navn": navn, "rang": rang},
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"OK – opprettet {created} nye roller"))
