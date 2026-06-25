from django.urls import path

from . import views

app_name = "planner"

urlpatterns = [
    path("", views.plan_setup, name="setup"),
    path("overview/", views.plan_overview, name="overview"),
    path("section-done/", views.plan_section_done, name="section_done"),
    path("complete/", views.plan_complete, name="complete"),
    path("abandon/", views.plan_abandon, name="abandon"),
]
