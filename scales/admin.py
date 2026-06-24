from django.contrib import admin

from .models import ScaleLog, ScalePractice, ScaleType


@admin.register(ScaleType)
class ScaleTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "slug"]
    list_filter = ["category"]
    search_fields = ["name", "slug"]
    readonly_fields = ["slug"]


@admin.register(ScalePractice)
class ScalePracticeAdmin(admin.ModelAdmin):
    list_display = ["__str__", "profile", "enabled", "sm2_enabled", "fastest_tempo", "next_review_at"]
    list_filter = ["enabled", "sm2_enabled", "profile"]
    readonly_fields = ["created_at", "ease_factor", "interval_days", "repetitions", "next_review_at"]


@admin.register(ScaleLog)
class ScaleLogAdmin(admin.ModelAdmin):
    list_display = ["scale_practice", "reviewed_at", "achieved_tempo", "rating"]
    list_filter = ["rating"]
    readonly_fields = ["reviewed_at"]
