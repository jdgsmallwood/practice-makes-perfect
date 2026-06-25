import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Instrument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=100)),
                ("midi_low", models.PositiveSmallIntegerField(default=60)),
                ("midi_high", models.PositiveSmallIntegerField(default=96)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="profile",
            name="instrument_fk",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="accounts.instrument",
            ),
        ),
    ]
