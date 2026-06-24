"""Seed the ScaleType table from scales/catalog.py.

Uses update_or_create so re-running is safe and new catalog entries can be
added in future migrations.
"""
from django.db import migrations


def seed_catalog(apps, schema_editor):
    from scales.catalog import CATALOG
    ScaleType = apps.get_model("scales", "ScaleType")
    for entry in CATALOG:
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
        ("scales", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_catalog, reverse_code=noop),
    ]
