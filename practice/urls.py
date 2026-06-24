from django.urls import path

from . import views

app_name = "practice"

urlpatterns = [
    path("", views.practice_session, name="session"),
    path("rate/", views.rate_bit, name="rate"),
    path("skip/", views.skip_bit, name="skip"),
    path("complete/", views.complete, name="complete"),
]
