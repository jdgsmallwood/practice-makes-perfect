from django.db import migrations

INSTRUMENTS = [
    {"slug": "alto_flute",  "name": "Alto Flute",  "midi_low": 55,  "midi_high": 91},
    {"slug": "bass_flute",  "name": "Bass Flute",  "midi_low": 48,  "midi_high": 84},
    {"slug": "clarinet",    "name": "Clarinet",    "midi_low": 50,  "midi_high": 94},
    {"slug": "cornet",      "name": "Cornet",      "midi_low": 54,  "midi_high": 82},
    {"slug": "flugelhorn",  "name": "Flugelhorn",  "midi_low": 54,  "midi_high": 77},
    {"slug": "flute",       "name": "Flute",       "midi_low": 60,  "midi_high": 96},
    {"slug": "oboe",        "name": "Oboe",        "midi_low": 58,  "midi_high": 91},
    {"slug": "other",       "name": "Other",       "midi_low": 60,  "midi_high": 96},
    {"slug": "piano",       "name": "Piano",       "midi_low": 21,  "midi_high": 108},
    {"slug": "piccolo",     "name": "Piccolo",     "midi_low": 74,  "midi_high": 96},
    {"slug": "saxophone",   "name": "Saxophone",   "midi_low": 49,  "midi_high": 80},
    {"slug": "trombone",    "name": "Trombone",    "midi_low": 40,  "midi_high": 72},
    {"slug": "trumpet",     "name": "Trumpet",     "midi_low": 54,  "midi_high": 82},
    {"slug": "violin",      "name": "Violin",      "midi_low": 55,  "midi_high": 100},
]


def populate(apps, schema_editor):
    Instrument = apps.get_model("accounts", "Instrument")
    Profile = apps.get_model("accounts", "Profile")

    for data in INSTRUMENTS:
        Instrument.objects.create(**data)

    instrument_map = {i.slug: i for i in Instrument.objects.all()}
    fallback = instrument_map["other"]

    for profile in Profile.objects.all():
        old_slug = profile.instrument  # still the old CharField at this point
        profile.instrument_fk = instrument_map.get(old_slug, fallback)
        profile.save(update_fields=["instrument_fk"])


def depopulate(apps, schema_editor):
    Instrument = apps.get_model("accounts", "Instrument")
    Instrument.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_instrument_add_fk"),
    ]

    operations = [
        migrations.RunPython(populate, depopulate),
    ]
