import zoneinfo

from django.utils import timezone


class TimezoneMiddleware:
    """Activate the user's local timezone from the browser-set cookie."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = request.COOKIES.get("timezone")
        if tzname:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tzname))
            except (KeyError, zoneinfo.ZoneInfoNotFoundError):
                timezone.deactivate()
        else:
            timezone.deactivate()
        return self.get_response(request)
