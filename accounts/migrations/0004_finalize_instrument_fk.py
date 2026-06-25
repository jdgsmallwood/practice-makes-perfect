from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_populate_instruments"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="instrument",
        ),
        migrations.RenameField(
            model_name="profile",
            old_name="instrument_fk",
            new_name="instrument",
        ),
    ]
