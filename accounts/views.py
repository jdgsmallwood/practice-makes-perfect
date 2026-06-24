from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm
from .models import Profile
from .utils import get_active_profile, set_active_profile


@login_required
def profile_list(request):
    profiles = Profile.objects.filter(user=request.user)
    active = get_active_profile(request)
    return render(request, "accounts/profile_list.html", {
        "profiles": profiles,
        "active_profile": active,
    })


@login_required
def profile_add(request):
    form = ProfileForm(request.POST or None)
    if form.is_valid():
        profile = form.save(commit=False)
        profile.user = request.user
        profile.save()
        set_active_profile(request, profile)
        return redirect("pieces:dashboard")
    return render(request, "accounts/profile_form.html", {"form": form, "action": "Add Profile"})


@login_required
def profile_edit(request, pk):
    profile = get_object_or_404(Profile, pk=pk, user=request.user)
    form = ProfileForm(request.POST or None, instance=profile)
    if form.is_valid():
        form.save()
        return redirect("accounts:profile_list")
    return render(request, "accounts/profile_form.html", {
        "form": form,
        "profile": profile,
        "action": "Edit Profile",
    })


@login_required
def profile_switch(request, pk):
    profile = get_object_or_404(Profile, pk=pk, user=request.user)
    set_active_profile(request, profile)
    # Clear session practice state so a new session starts fresh for this profile
    request.session.pop("skipped_bits", None)
    request.session.pop("practice_order", None)
    return redirect(request.GET.get("next", "pieces:dashboard"))


@login_required
def profile_delete(request, pk):
    profile = get_object_or_404(Profile, pk=pk, user=request.user)
    if request.method == "POST":
        # Switch active profile if we're deleting the current one
        active = get_active_profile(request)
        if active and active.pk == profile.pk:
            request.session.pop("active_profile_id", None)
        profile.delete()
        return redirect("accounts:profile_list")
    return render(request, "accounts/profile_confirm_delete.html", {"profile": profile})
