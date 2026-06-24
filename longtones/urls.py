from django.urls import path

from . import views

app_name = "longtones"

urlpatterns = [
    path("",              views.home,      name="home"),
    path("session/",      views.session,   name="session"),
    path("session/log/",  views.log_note,  name="log_note"),
    path("session/skip/", views.skip,      name="skip"),
    path("complete/",     views.complete,  name="complete"),
]
