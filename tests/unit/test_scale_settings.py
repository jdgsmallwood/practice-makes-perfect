import pytest
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone

from scales.models import ScaleType, ScalePractice, ScaleLog
from scales.catalog import ROOTS


@pytest.mark.django_db
def test_enabled_cells_render_selected_regardless_of_recency(logged_in_client_with_profile):
    """An enabled scale must look selected (indigo) even if practiced long ago.

    Regression: previously the grid shaded enabled-but-stale scales amber, so
    they looked unselected.
    """
    client, profile = logged_in_client_with_profile
    st = ScaleType.objects.create(slug="major", name="Major (Ionian)",
                                  category="Diatonic Modes", intervals=[0, 2, 4, 5, 7, 9, 11])
    practices = {r: ScalePractice.objects.create(profile=profile, scale_type=st, root=r, enabled=True)
                 for r in range(12)}
    # D#/Eb (3) and A (9): practiced 10 days ago (previously rendered amber).
    for r in (3, 9):
        log = ScaleLog.objects.create(scale_practice=practices[r], rating=3)
        ScaleLog.objects.filter(pk=log.pk).update(reviewed_at=timezone.now() - timedelta(days=10))

    html = client.get(reverse("scales:settings")).content.decode()
    for r in range(12):
        i = html.find(f'scale-toggle-{st.pk}-{r}')
        block = html[i:i+260]
        assert "bg-indigo-600" in block, f"{ROOTS[r]} not rendered as selected"
        assert "amber" not in block, f"{ROOTS[r]} rendered with stale (amber) shading"
        assert "bg-gray-800" not in block, f"{ROOTS[r]} rendered as unselected"
