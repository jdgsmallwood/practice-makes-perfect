from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScaleType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=60, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("category", models.CharField(max_length=60)),
                ("intervals", models.JSONField()),
                ("description", models.TextField(blank=True)),
            ],
            options={"ordering": ["category", "name"]},
        ),
        migrations.CreateModel(
            name="ScalePractice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("root", models.PositiveSmallIntegerField(choices=[
                    (0, "C"), (1, "C#/Db"), (2, "D"), (3, "D#/Eb"), (4, "E"), (5, "F"),
                    (6, "F#/Gb"), (7, "G"), (8, "G#/Ab"), (9, "A"), (10, "A#/Bb"), (11, "B"),
                ])),
                ("enabled", models.BooleanField(default=False)),
                ("desired_tempo", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("current_tempo", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("fastest_tempo", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("sm2_enabled", models.BooleanField(default=False)),
                ("ease_factor", models.FloatField(default=2.5)),
                ("interval_days", models.IntegerField(default=0)),
                ("repetitions", models.IntegerField(default=0)),
                ("next_review_at", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("profile", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="scale_practices",
                    to="accounts.profile",
                )),
                ("scale_type", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="practices",
                    to="scales.scaletype",
                )),
            ],
            options={
                "ordering": ["scale_type__category", "scale_type__name", "root"],
                "unique_together": {("profile", "scale_type", "root")},
            },
        ),
        migrations.CreateModel(
            name="ScaleLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reviewed_at", models.DateTimeField(auto_now_add=True)),
                ("achieved_tempo", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("rating", models.PositiveSmallIntegerField(
                    blank=True,
                    null=True,
                    choices=[(1, "Again"), (2, "Hard"), (3, "Good"), (4, "Easy")],
                )),
                ("interval_before", models.IntegerField(blank=True, null=True)),
                ("interval_after", models.IntegerField(blank=True, null=True)),
                ("scale_practice", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="logs",
                    to="scales.scalepractice",
                )),
            ],
            options={"ordering": ["-reviewed_at"]},
        ),
    ]
