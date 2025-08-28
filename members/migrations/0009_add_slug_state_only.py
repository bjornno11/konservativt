from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("members", "0008_lokallag_contact_email_lokallag_contact_phone_and_more"),
    ]

    operations = [
        # Hvis 0008 allerede la slug i state, gjør denne migrasjonen ingenting (no-op).
        # Hvis 0008 IKKE la slug i state, legger vi kun til feltet i STATE (ikke DB).
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # DB er håndtert manuelt i steg 1
            state_operations=[
                # Denne AddField er "idempotent" i state:
                # - Hvis feltet allerede finnes i state: Django ignorerer/optimaliserer det bort.
                # - Hvis det ikke finnes: det legges til i state.
                migrations.AddField(
                    model_name="lokallag",
                    name="slug",
                    field=models.SlugField(max_length=140, blank=True, null=True),
                ),
            ],
        ),
    ]
