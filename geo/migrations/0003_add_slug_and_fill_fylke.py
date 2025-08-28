from django.db import migrations, models
from django.utils.text import slugify

def populate_fylke_slugs(apps, schema_editor):
    Fylke = apps.get_model("geo", "Fylke")
    used = set(
        s for s in Fylke.objects
            .exclude(slug__isnull=True)
            .exclude(slug="")
            .values_list("slug", flat=True)
    )
    for obj in Fylke.objects.all():
        if obj.slug:
            base = obj.slug
        else:
            base = slugify(obj.navn) or f"fylke-{obj.pk}"
        slug = base
        i = 2
        while slug in used:
            slug = f"{base}-{i}"
            i += 1
        obj.slug = slug
        obj.save(update_fields=["slug"])
        used.add(slug)

class Migration(migrations.Migration):

    dependencies = [
        ("geo", "0002_fylke_contact_email_fylke_contact_phone_and_more"),
    ]

    operations = [
        # 1) Legg til feltet uten unique-constraint og tillat NULL
        migrations.AddField(
            model_name="fylke",
            name="slug",
            field=models.SlugField(max_length=120, blank=True, null=True),
        ),
        # 2) Fyll inn unike slugs for eksisterende rader
        migrations.RunPython(populate_fylke_slugs, migrations.RunPython.noop),
        # 3) Stram inn til unique=True (NULL beholdes)
        migrations.AlterField(
            model_name="fylke",
            name="slug",
            field=models.SlugField(max_length=120, blank=True, null=True, unique=True),
        ),
    ]
