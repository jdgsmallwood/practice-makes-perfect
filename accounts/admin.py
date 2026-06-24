from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "instrument", "user", "created_at"]
    list_filter = ["instrument"]
    search_fields = ["name", "user__username"]
    readonly_fields = ["created_at"]
