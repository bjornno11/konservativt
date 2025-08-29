from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = "Opprett gruppen 'sentralstyret' og legg til en bruker (valgfritt)."

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Brukernavn å legge i sentralstyret", default=None)

    def handle(self, *args, **opts):
        g, created = Group.objects.get_or_create(name="sentralstyret")
        if created:
            self.stdout.write(self.style.SUCCESS("Opprettet gruppe 'sentralstyret'"))
        else:
            self.stdout.write("Gruppe 'sentralstyret' finnes allerede")

        if opts["username"]:
            U = get_user_model()
            u = U.objects.filter(username=opts["username"]).first()
            if not u:
                self.stderr.write(f"Fant ikke bruker '{opts['username']}'")
                return
            u.groups.add(g)
            self.stdout.write(self.style.SUCCESS(f"La '{u.username}' i gruppen 'sentralstyret'"))
