"""Seed AMEB-relevant scale types: Chromatic, Arpeggios, Broken Chords, Scales in Thirds."""
from django.db import migrations


def seed_new_types(apps, schema_editor):
    from scales.catalog import CATALOG
    ScaleType = apps.get_model("scales", "ScaleType")
    new_categories = {"Chromatic", "Arpeggios", "Broken Chords", "Scales in Thirds"}
    for entry in CATALOG:
        if entry["category"] in new_categories:
            ScaleType.objects.update_or_create(
                slug=entry["slug"],
                defaults={
                    "name": entry["name"],
                    "category": entry["category"],
                    "intervals": entry["intervals"],
                    "description": entry.get("description", ""),
                },
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("scales", "0002_seed_catalog"),
    ]

    operations = [
        migrations.RunPython(seed_new_types, reverse_code=noop),
    ]
