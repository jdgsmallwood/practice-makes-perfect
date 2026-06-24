from django.db import models

from .catalog import ROOTS


class ScaleType(models.Model):
    slug = models.SlugField(unique=True, max_length=60)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=60)
    intervals = models.JSONField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class ScalePractice(models.Model):
    ROOT_CHOICES = [(i, name) for i, name in enumerate(ROOTS)]

    profile = models.ForeignKey(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="scale_practices",
    )
    scale_type = models.ForeignKey(ScaleType, on_delete=models.CASCADE, related_name="practices")
    root = models.PositiveSmallIntegerField(choices=ROOT_CHOICES)
    enabled = models.BooleanField(default=False)

    desired_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    current_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    fastest_tempo = models.PositiveSmallIntegerField(null=True, blank=True)

    # SM-2 state (only used when sm2_enabled)
    sm2_enabled = models.BooleanField(default=False)
    ease_factor = models.FloatField(default=2.5)
    interval_days = models.IntegerField(default=0)
    repetitions = models.IntegerField(default=0)
    next_review_at = models.DateField(null=True, blank=True)

    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("profile", "scale_type", "root")]
        ordering = ["scale_type__category", "scale_type__name", "root"]

    def __str__(self):
        return f"{ROOTS[self.root]} {self.scale_type.name}"

    def is_sm2_due(self):
        from datetime import date
        return self.sm2_enabled and (
            self.next_review_at is None or self.next_review_at <= date.today()
        )


class ScaleLog(models.Model):
    RATING_CHOICES = [
        (1, "Again"),
        (2, "Hard"),
        (3, "Good"),
        (4, "Easy"),
    ]

    scale_practice = models.ForeignKey(
        ScalePractice,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    reviewed_at = models.DateTimeField(auto_now_add=True)
    achieved_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, null=True, blank=True)
    interval_before = models.IntegerField(null=True, blank=True)
    interval_after = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-reviewed_at"]

    def __str__(self):
        return f"{self.scale_practice} — {self.reviewed_at:%Y-%m-%d}"
