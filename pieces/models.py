from datetime import date

from django.db import models


class Piece(models.Model):
    name = models.CharField(max_length=255)
    composer = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    profile = models.ForeignKey(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="pieces",
        null=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TrickyBit(models.Model):
    DIFFICULTY_CHOICES = [(i, str(i)) for i in range(1, 6)]

    KEY_SIGNATURE_CHOICES = [
        ("", "— none —"),
        # Major
        ("C", "C major"),
        ("G", "G major (1♯)"),
        ("D", "D major (2♯)"),
        ("A", "A major (3♯)"),
        ("E", "E major (4♯)"),
        ("B", "B major (5♯)"),
        ("F#", "F♯ major (6♯)"),
        ("C#", "C♯ major (7♯)"),
        ("F", "F major (1♭)"),
        ("Bb", "B♭ major (2♭)"),
        ("Eb", "E♭ major (3♭)"),
        ("Ab", "A♭ major (4♭)"),
        ("Db", "D♭ major (5♭)"),
        ("Gb", "G♭ major (6♭)"),
        ("Cb", "C♭ major (7♭)"),
        # Minor
        ("Am", "A minor"),
        ("Em", "E minor (1♯)"),
        ("Bm", "B minor (2♯)"),
        ("F#m", "F♯ minor (3♯)"),
        ("C#m", "C♯ minor (4♯)"),
        ("G#m", "G♯ minor (5♯)"),
        ("D#m", "D♯ minor (6♯)"),
        ("A#m", "A♯ minor (7♯)"),
        ("Dm", "D minor (1♭)"),
        ("Gm", "G minor (2♭)"),
        ("Cm", "C minor (3♭)"),
        ("Fm", "F minor (4♭)"),
        ("Bbm", "B♭ minor (5♭)"),
        ("Ebm", "E♭ minor (6♭)"),
        ("Abm", "A♭ minor (7♭)"),
    ]

    piece = models.ForeignKey(Piece, on_delete=models.CASCADE, related_name="tricky_bits")
    label = models.CharField(max_length=255)
    image = models.ImageField(upload_to="tricky_bits/%Y/%m/", blank=True, null=True)
    description = models.TextField(blank=True)
    desired_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    current_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    difficulty = models.PositiveSmallIntegerField(default=3, choices=DIFFICULTY_CHOICES)
    key_signature = models.CharField(max_length=4, blank=True, default="", choices=KEY_SIGNATURE_CHOICES)
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
    achieved_tempo = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-reviewed_at"]

    def __str__(self):
        return f"{self.tricky_bit.label} — {self.get_rating_display()} @ {self.reviewed_at:%Y-%m-%d}"
