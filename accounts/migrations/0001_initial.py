from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("instrument", models.CharField(
                    choices=[
                        ("flute", "Flute"),
                        ("piccolo", "Piccolo"),
                        ("alto_flute", "Alto Flute"),
                        ("bass_flute", "Bass Flute"),
                        ("clarinet", "Clarinet"),
                        ("oboe", "Oboe"),
                        ("saxophone", "Saxophone"),
                        ("violin", "Violin"),
                        ("piano", "Piano"),
                        ("other", "Other"),
                    ],
                    default="flute",
                    max_length=20,
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="profiles",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["name"]},
        ),
    ]
