from django.contrib import admin

from .models import LongToneLog, LongToneSession


@admin.register(LongToneSession)
class LongToneSessionAdmin(admin.ModelAdmin):
    list_display = ["profile", "date", "focus", "use_drone", "started_at", "completed_at"]
    list_filter = ["focus", "profile"]
    readonly_fields = ["started_at", "completed_at"]


@admin.register(LongToneLog)
class LongToneLogAdmin(admin.ModelAdmin):
    list_display = ["session", "note_name", "midi", "rating", "logged_at"]
    list_filter = ["rating", "session__focus"]
    readonly_fields = ["logged_at"]
