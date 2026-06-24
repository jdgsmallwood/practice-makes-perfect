from django.urls import path

from . import views

app_name = "pieces"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("pieces/", views.piece_list, name="piece_list"),
    path("pieces/add/", views.piece_add, name="piece_add"),
    path("pieces/<int:pk>/", views.piece_detail, name="piece_detail"),
    path("pieces/<int:pk>/edit/", views.piece_edit, name="piece_edit"),
    path("pieces/<int:pk>/toggle/", views.piece_toggle_active, name="piece_toggle"),
    path("pieces/upload-image/", views.upload_image_ajax, name="upload_image"),
    path("pieces/<int:pk>/bits/add/", views.trickybit_add, name="trickybit_add"),
    path("pieces/<int:pk>/bits/<int:bit_pk>/", views.trickybit_detail, name="trickybit_detail"),
    path("pieces/<int:pk>/bits/<int:bit_pk>/edit/", views.trickybit_edit, name="trickybit_edit"),
    path("pieces/<int:pk>/bits/<int:bit_pk>/reset/", views.trickybit_reset, name="trickybit_reset"),
    path("pieces/<int:pk>/bits/<int:bit_pk>/delete/", views.trickybit_delete, name="trickybit_delete"),
]
