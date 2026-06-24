from datetime import date

from django.db import models


class Piece(models.Model):
    name = models.CharField(max_length=255)
    composer = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TrickyBit(models.Model):
    DIFFICULTY_CHOICES = [(i, str(i)) for i in range(1, 6)]

    piece = models.ForeignKey(Piece, on_delete=models.CASCADE, related_name="tricky_bits")
    label = models.CharField(max_length=255)
    image = models.ImageField(upload_to="tricky_bits/%Y/%m/", blank=True, null=True)
    description = models.TextField(blank=True)
    desired_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    current_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    difficulty = models.PositiveSmallIntegerField(default=3, choices=DIFFICULTY_CHOICES)
    tags = models.CharField(max_length=500, blank=True)

    # SM-2 spaced repetition state
    ease_factor = models.FloatField(default=2.5)
    interval_days = models.IntegerField(default=0)
    repetitions = models.IntegerField(default=0)
    next_review_at = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return f"{self.piece.name} — {self.label}"

    def is_due(self):
        return self.next_review_at is None or self.next_review_at <= date.today()

    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]


class PracticeLog(models.Model):
    RATING_CHOICES = [
        (1, "Again"),
        (2, "Hard"),
        (3, "Good"),
        (4, "Easy"),
    ]

    tricky_bit = models.ForeignKey(
        TrickyBit, on_delete=models.CASCADE, related_name="practice_logs"
    )
    reviewed_at = models.DateTimeField(auto_now_add=True)
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    interval_before = models.IntegerField()
    interval_after = models.IntegerField()

    class Meta:
        ordering = ["-reviewed_at"]

    def __str__(self):
        return f"{self.tricky_bit.label} — {self.get_rating_display()} @ {self.reviewed_at:%Y-%m-%d}"
