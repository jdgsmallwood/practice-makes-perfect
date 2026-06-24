from django.db import models

from pieces.models import TrickyBit

FEATURE_CHOICES = [
    # Register
    ("register_low", "Low register (below C4)"),
    ("register_middle", "Middle register (C4–C6)"),
    ("register_high", "High register (C6+)"),
    ("register_altissimo", "Altissimo (C7+)"),
    # Intervals
    ("interval_stepwise", "Stepwise motion"),
    ("interval_thirds", "Thirds"),
    ("interval_fourths_fifths", "Fourths / fifths"),
    ("interval_sixths", "Sixths"),
    ("interval_octaves", "Octaves"),
    ("interval_wide_leaps", "Wide leaps (> octave)"),
    # Technique
    ("technique_slur", "Slurs / legato"),
    ("technique_staccato", "Staccato"),
    ("technique_trill", "Trill"),
    ("technique_flutter", "Flutter tongue"),
    ("technique_harmonic", "Harmonics"),
    ("technique_multiphonic", "Multiphonics"),
    ("technique_vibrato", "Vibrato notation"),
    # Rhythm
    ("rhythm_fast_runs", "Fast scalar runs"),
    ("rhythm_triplets", "Triplets"),
    ("rhythm_dotted", "Dotted rhythms"),
    ("rhythm_syncopation", "Syncopation"),
    ("rhythm_cross_rhythm", "Cross rhythms / hemiola"),
    # Articulation marks
    ("mark_accent", "Accents (>)"),
    ("mark_tenuto", "Tenuto (—)"),
    ("mark_marcato", "Marcato (^)"),
    # Dynamics
    ("dynamic_soft", "Soft dynamics (pp / p)"),
    ("dynamic_loud", "Loud dynamics (ff / f)"),
    ("dynamic_sudden_change", "Sudden dynamic changes"),
    # Key & time
    ("key_many_sharps", "Many sharps (3+)"),
    ("key_many_flats", "Many flats (3+)"),
    ("time_compound", "Compound time (6/8, 9/8)"),
    ("time_irregular", "Irregular meter (5/4, 7/8)"),
    ("time_changing", "Changing time signatures"),
]

# Grouped for rendering checkboxes in the UI
FEATURE_GROUPS = [
    ("Register", [
        "register_low", "register_middle", "register_high", "register_altissimo",
    ]),
    ("Intervals", [
        "interval_stepwise", "interval_thirds", "interval_fourths_fifths",
        "interval_sixths", "interval_octaves", "interval_wide_leaps",
    ]),
    ("Techniques", [
        "technique_slur", "technique_staccato", "technique_trill",
        "technique_flutter", "technique_harmonic", "technique_multiphonic",
        "technique_vibrato",
    ]),
    ("Rhythm", [
        "rhythm_fast_runs", "rhythm_triplets", "rhythm_dotted",
        "rhythm_syncopation", "rhythm_cross_rhythm",
    ]),
    ("Articulation", ["mark_accent", "mark_tenuto", "mark_marcato"]),
    ("Dynamics", ["dynamic_soft", "dynamic_loud", "dynamic_sudden_change"]),
    ("Key & Time", [
        "key_many_sharps", "key_many_flats",
        "time_compound", "time_irregular", "time_changing",
    ]),
]

FEATURE_LABELS = dict(FEATURE_CHOICES)


class PassageAnalysis(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("complete", "Complete"),
        ("failed", "Failed"),
    ]
    PROVIDER_CHOICES = [
        ("manual", "Manual"),
        ("claude_vision", "Claude Vision AI"),
    ]

    tricky_bit = models.OneToOneField(
        TrickyBit, on_delete=models.CASCADE, related_name="analysis"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES, default="manual")
    notes = models.TextField(blank=True)
    raw_response = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "passage analysis"
        verbose_name_plural = "passage analyses"

    def __str__(self):
        return f"Analysis of '{self.tricky_bit.label}' ({self.status})"

    @property
    def detected_feature_types(self):
        return set(self.detected_features.values_list("feature_type", flat=True))


class DetectedFeature(models.Model):
    analysis = models.ForeignKey(
        PassageAnalysis, on_delete=models.CASCADE, related_name="detected_features"
    )
    feature_type = models.CharField(max_length=50, choices=FEATURE_CHOICES)
    confidence = models.FloatField(default=1.0)

    class Meta:
        unique_together = [("analysis", "feature_type")]
        ordering = ["feature_type"]

    def __str__(self):
        return f"{self.get_feature_type_display()} ({self.confidence:.0%})"


class Exercise(models.Model):
    """Practice exercises targeting specific musical features.

    The target_features list holds feature_type codes from FEATURE_CHOICES.
    Used to recommend exercises when a passage's analysis shares those features.
    """
    title = models.CharField(max_length=255)
    description = models.TextField()
    target_features = models.JSONField(
        default=list,
        help_text="List of feature_type codes this exercise targets.",
    )
    difficulty = models.PositiveSmallIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["difficulty", "title"]

    def __str__(self):
        return self.title
