from django.contrib import admin

from .models import ArticulationLog, ArticulationSession


@admin.register(ArticulationSession)
class ArticulationSessionAdmin(admin.ModelAdmin):
    list_display    = ["profile", "date", "track", "started_at", "completed_at"]
    list_filter     = ["track", "profile"]
    readonly_fields = ["started_at", "completed_at"]


@admin.register(ArticulationLog)
class ArticulationLogAdmin(admin.ModelAdmin):
    list_display    = ["session", "exercise_id", "rating", "logged_at"]
    list_filter     = ["rating", "exercise_id", "session__track"]
    readonly_fields = ["logged_at"]
