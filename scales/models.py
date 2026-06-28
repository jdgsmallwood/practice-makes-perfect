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

    repetitions = models.IntegerField(default=0)

    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("profile", "scale_type", "root")]
        ordering = ["scale_type__category", "scale_type__name", "root"]

    def __str__(self):
        return f"{ROOTS[self.root]} {self.scale_type.name}"


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

    class Meta:
        ordering = ["-reviewed_at"]

    def __str__(self):
        return f"{self.scale_practice} — {self.reviewed_at:%Y-%m-%d}"
