from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("pieces", "0002_practicelog_achieved_tempo"),
    ]

    operations = [
        migrations.AddField(
            model_name="piece",
            name="profile",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="pieces",
                to="accounts.profile",
            ),
        ),
    ]
