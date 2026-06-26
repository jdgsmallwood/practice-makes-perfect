import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Use an in-memory SQLite database for all tests."""
    pass


@pytest.fixture
def logged_in_client(db):
    """Django test client authenticated as a user with no profile.

    Views that filter by active profile (None) will match pieces/bits that
    also have profile=None, so factory-created objects without a profile are
    still found by these views.
    """
    from django.contrib.auth.models import User
    from django.test import Client

    user = User.objects.create_user("testuser", password="test")
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def logged_in_client_with_profile(db):
    """Django test client authenticated as a user who has an active Profile.

    Use for views that require get_active_profile() to return a non-None value
    (e.g. scales views that use profile as a FK on ScalePractice).
    Returns (client, profile).
    """
    from django.contrib.auth.models import User
    from django.test import Client
    from accounts.models import Profile
    from accounts.utils import SESSION_KEY as PROFILE_SESSION_KEY

    user = User.objects.create_user("profileuser", password="test")
    profile = Profile.objects.create(user=user, name="Test")

    c = Client()
    c.force_login(user)
    session = c.session
    session[PROFILE_SESSION_KEY] = profile.pk
    session.save()
    return c, profile
