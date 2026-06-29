from django.contrib import admin

from .models import TransitionLog, TransitionPractice, TransitionSession


@admin.register(TransitionPractice)
class TransitionPracticeAdmin(admin.ModelAdmin):
    list_display = ("profile", "name_low", "name_high", "status", "position", "fastest_tempo")
    list_filter = ("status",)
    search_fields = ("profile__name", "notes")


@admin.register(TransitionSession)
class TransitionSessionAdmin(admin.ModelAdmin):
    list_display = ("profile", "date", "started_at", "completed_at")
    list_filter = ("date",)


@admin.register(TransitionLog)
class TransitionLogAdmin(admin.ModelAdmin):
    list_display = ("transition_practice", "exercise_id", "rating", "achieved_tempo", "logged_at")
    list_filter = ("exercise_id", "rating")
