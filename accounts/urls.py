from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.profile_list, name="profile_list"),
    path("add/", views.profile_add, name="profile_add"),
    path("<int:pk>/edit/", views.profile_edit, name="profile_edit"),
    path("<int:pk>/switch/", views.profile_switch, name="profile_switch"),
    path("<int:pk>/delete/", views.profile_delete, name="profile_delete"),
]
