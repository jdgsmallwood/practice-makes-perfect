import os

import pytest

# pytest-playwright runs an asyncio event loop, which causes Django's
# async guard to raise SynchronousOnlyOperation on ORM calls in tests.
# This flag tells Django to allow synchronous DB access from that context.
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Default to a desktop viewport that matches iPad Pro landscape."""
    return {
        **browser_context_args,
        "viewport": {"width": 1366, "height": 1024},
    }


@pytest.fixture(autouse=True)
def auto_login(page, live_server, django_user_model):
    """Inject a Django session cookie into every E2E test's browser context.

    Creates the session directly in the database and injects the cookie so the
    browser is authenticated without going through the login form. Uses
    get_or_create so repeated calls within the same session are safe.
    """
    from django.conf import settings
    from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
    from django.contrib.sessions.backends.db import SessionStore

    user, _ = django_user_model.objects.get_or_create(username="testuser")

    session = SessionStore()
    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()

    page.context.add_cookies([{
        "name": settings.SESSION_COOKIE_NAME,
        "value": session.session_key,
        "url": live_server.url,
    }])


@pytest.fixture
def with_profile(page, live_server, django_user_model):
    """Ensures testuser has a flute profile and the active session knows about it.

    Many sections (longtones, articulation) require an active Profile via
    get_active_profile(). This fixture creates one for testuser and writes
    its pk into the Django session so views resolve it correctly.

    Depends on auto_login (autouse=True) having already set the session cookie.
    """
    from accounts.models import Profile
    from accounts.utils import SESSION_KEY as PROFILE_SESSION_KEY
    from django.contrib.sessions.backends.db import SessionStore

    user, _ = django_user_model.objects.get_or_create(username="testuser")
    profile, _ = Profile.objects.get_or_create(
        user=user, defaults={"name": "Test Flutist", "instrument": "flute"}
    )
    for cookie in page.context.cookies():
        if cookie["name"] == "sessionid":
            session = SessionStore(session_key=cookie["value"])
            session[PROFILE_SESSION_KEY] = profile.pk
            session.save()
            break
    return profile
