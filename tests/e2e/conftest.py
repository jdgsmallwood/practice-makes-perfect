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
