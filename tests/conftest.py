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
