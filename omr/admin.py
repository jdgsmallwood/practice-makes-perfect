from django.contrib import admin

from .models import DetectedFeature, Exercise, PassageAnalysis


class DetectedFeatureInline(admin.TabularInline):
    model = DetectedFeature
    extra = 0
    readonly_fields = ["feature_type", "confidence"]


@admin.register(PassageAnalysis)
class PassageAnalysisAdmin(admin.ModelAdmin):
    list_display = ["tricky_bit", "provider", "status", "updated_at"]
    list_filter = ["status", "provider"]
    readonly_fields = ["tricky_bit", "raw_response", "created_at", "updated_at", "completed_at"]
    inlines = [DetectedFeatureInline]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ["title", "difficulty", "target_features"]
    list_filter = ["difficulty"]
    search_fields = ["title", "description"]
