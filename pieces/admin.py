from django.contrib import admin

from .models import Piece, PracticeLog, TrickyBit


@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ["name", "composer", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "composer"]
    list_editable = ["is_active"]


@admin.register(TrickyBit)
class TrickyBitAdmin(admin.ModelAdmin):
    list_display = ["label", "piece", "difficulty", "next_review_at", "ease_factor", "repetitions"]
    list_filter = ["piece", "difficulty"]
    search_fields = ["label", "tags"]
    readonly_fields = ["ease_factor", "interval_days", "repetitions", "next_review_at"]


@admin.register(PracticeLog)
class PracticeLogAdmin(admin.ModelAdmin):
    list_display = ["tricky_bit", "rating", "reviewed_at", "interval_before", "interval_after"]
    list_filter = ["rating"]
    date_hierarchy = "reviewed_at"
    readonly_fields = ["reviewed_at"]
