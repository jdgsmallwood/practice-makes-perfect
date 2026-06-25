from django.urls import path

from . import views

app_name = "articulation"

urlpatterns = [
    path("",               views.home,         name="home"),
    path("session/",       views.session,      name="session"),
    path("session/log/",   views.log_exercise, name="log_exercise"),
    path("session/skip/",  views.skip,         name="skip"),
    path("complete/",      views.complete,     name="complete"),
]
