from django.urls import path

from . import views

app_name = "omr"

urlpatterns = [
    path("bits/<int:bit_pk>/features/", views.save_manual_features, name="save_features"),
    path("bits/<int:bit_pk>/analyze/", views.analyze_with_ai, name="analyze_ai"),
]
