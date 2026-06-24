from .models import Profile
from .utils import get_active_profile


def active_profile(request):
    if not request.user.is_authenticated:
        return {}
    profile = get_active_profile(request)
    profiles = list(Profile.objects.filter(user=request.user))
    return {
        "active_profile": profile,
        "user_profiles": profiles,
    }
