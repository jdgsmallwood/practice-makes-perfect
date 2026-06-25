from django.db import migrations


def fix_brass(apps, schema_editor):
    Instrument = apps.get_model("accounts", "Instrument")
    Instrument.objects.filter(slug__in=["trumpet", "cornet", "flugelhorn"]).update(midi_low=54)


def revert_brass(apps, schema_editor):
    Instrument = apps.get_model("accounts", "Instrument")
    Instrument.objects.filter(slug__in=["trumpet", "cornet", "flugelhorn"]).update(midi_low=52)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_finalize_instrument_fk"),
    ]

    operations = [
        migrations.RunPython(fix_brass, revert_brass),
    ]
