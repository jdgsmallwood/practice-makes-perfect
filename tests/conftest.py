import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Use an in-memory SQLite database for all tests."""
    pass
