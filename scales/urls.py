from django.urls import path

from . import views

app_name = "scales"

urlpatterns = [
    path("", views.settings_view, name="settings"),
    path("toggle/<int:scale_type_id>/<int:root>/", views.toggle_scale, name="toggle"),
    path("toggle-all/<int:scale_type_id>/<str:action>/", views.toggle_all_roots, name="toggle_all"),
    path("rotation/", views.rotation_session, name="rotation_session"),
    path("rotation/log/", views.rotation_log, name="rotation_log"),
    path("rotation/skip/", views.rotation_skip, name="rotation_skip"),
    path("rotation/reshuffle/", views.rotation_reshuffle, name="rotation_reshuffle"),
    path("rotation/complete/", views.rotation_complete, name="rotation_complete"),
    path("sm2/", views.sm2_session, name="sm2_session"),
    path("sm2/rate/", views.sm2_rate, name="sm2_rate"),
    path("sm2/complete/", views.sm2_complete, name="sm2_complete"),
    path("practice/<int:pk>/", views.detail, name="detail"),
    path("practice/<int:pk>/log/", views.log_from_detail, name="log_from_detail"),
    path("practice/<int:pk>/sm2/", views.toggle_sm2, name="toggle_sm2"),
    path("practice/<int:pk>/tempo/", views.set_tempo, name="set_tempo"),
    path("practice/<int:pk>/notes/", views.save_notes, name="save_notes"),
    path("rotation/key/<int:root>/", views.rotation_by_key, name="rotation_by_key"),
]
