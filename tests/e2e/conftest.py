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
