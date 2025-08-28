from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("members", "0009_add_slug_state_only"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lokallag",
            name="slug",
            field=models.SlugField(max_length=140, blank=True, null=True, unique=True),
        ),
    ]
