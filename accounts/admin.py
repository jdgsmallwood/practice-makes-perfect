from django.contrib import admin

from .models import Instrument, Profile


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "midi_low", "midi_high"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "slug"]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "instrument", "user", "created_at"]
    list_filter = ["instrument"]
    search_fields = ["name", "user__username"]
    readonly_fields = ["created_at"]
