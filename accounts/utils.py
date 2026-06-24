from .models import Profile

SESSION_KEY = "active_profile_id"


def get_active_profile(request):
    """Return the currently active Profile for the logged-in user.

    Falls back to the user's first profile and persists that choice to the
    session so subsequent requests are fast (one query instead of two).
    Returns None if the user has no profiles yet.
    """
    if not request.user.is_authenticated:
        return None

    profile_id = request.session.get(SESSION_KEY)
    if profile_id:
        profile = Profile.objects.filter(pk=profile_id, user=request.user).first()
        if profile:
            return profile

    # Fall back to first profile
    profile = Profile.objects.filter(user=request.user).first()
    if profile:
        request.session[SESSION_KEY] = profile.pk
    return profile


def set_active_profile(request, profile):
    request.session[SESSION_KEY] = profile.pk
