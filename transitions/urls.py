from django.urls import path

from . import views

app_name = "transitions"

urlpatterns = [
    path("", views.home, name="home"),
    path("add/", views.add_transition, name="add_transition"),
    path("retire/", views.retire_transition, name="retire_transition"),
    path("remove/", views.remove_transition, name="remove_transition"),
    path("session/", views.session, name="session"),
    path("session/log/", views.log_transition, name="log_transition"),
    path("session/skip/", views.skip, name="skip"),
    path("complete/", views.complete, name="complete"),
]
