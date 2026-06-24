"""Assign all existing profile-less Pieces to a default user+profile.

The default username is read from the DEFAULT_USERNAME env var (falls back to
"justin"). A matching User is created with an unusable password so the account
exists but cannot log in until `manage.py changepassword <username>` is run.
"""
from django.db import migrations


def assign_default_profile(apps, schema_editor):
    import os

    User = apps.get_model("auth", "User")
    Profile = apps.get_model("accounts", "Profile")
    Piece = apps.get_model("pieces", "Piece")

    username = os.environ.get("DEFAULT_USERNAME", "justin")
    user, _ = User.objects.get_or_create(username=username)
    if not user.password or user.password == "":
        from django.contrib.auth.hashers import make_password
        user.password = make_password(None)  # unusable password
        user.save(update_fields=["password"])

    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={"name": "Flute", "instrument": "flute"},
    )

    Piece.objects.filter(profile__isnull=True).update(profile=profile)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("pieces", "0003_piece_profile"),
    ]

    operations = [
        migrations.RunPython(assign_default_profile, reverse_code=noop),
    ]
