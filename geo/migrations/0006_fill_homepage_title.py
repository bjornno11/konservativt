from django.db import migrations
from django.db.models import F


def forwards(apps, schema_editor):
    Fylke = apps.get_model("geo", "Fylke")
    # Sett homepage_title = navn der den er tom (eller NULL for sikkerhets skyld)
    (Fylke.objects
          .filter(homepage_title__in=["", None])
          .update(homepage_title=F("navn")))


def backwards(apps, schema_editor):
    # Revers: bare null ut titler som er identiske med navn (vi antar at disse kom fra denne migrasjonen)
    Fylke = apps.get_model("geo", "Fylke")
    from django.db.models.functions import NullIf
    # For MySQL-kompat, gjør en to-trinns «best effort»:
    # 1) Finn rader der homepage_title == navn og sett til tom streng
    qs = Fylke.objects.all().only("id", "homepage_title", "navn")
    ids = [f.id for f in qs if (f.homepage_title or "") == (f.navn or "")]
    if ids:
        Fylke.objects.filter(id__in=ids).update(homepage_title="")


class Migration(migrations.Migration):

    dependencies = [
        # Sørg for at denne kommer ETTER migrasjonen som la til feltene dine.
        # Juster nums under til din siste geo-migrasjon.
        ("geo", "0005_fylke_homepage_public"),

    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
