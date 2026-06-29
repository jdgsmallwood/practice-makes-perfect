from django.core.exceptions import ValidationError
from django.db import models

from .utils import MIDI_NAMES


class TransitionPractice(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_QUEUED = "queued"
    STATUS_RETIRED = "retired"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_QUEUED, "Queued"),
        (STATUS_RETIRED, "Retired"),
    ]

    profile = models.ForeignKey(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="transition_practices",
    )
    note_low = models.PositiveSmallIntegerField()
    note_high = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    position = models.PositiveSmallIntegerField(default=0)
    current_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    fastest_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    desired_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("profile", "note_low", "note_high")]
        ordering = ["status", "position", "created_at"]

    @property
    def interval_semitones(self):
        return self.note_high - self.note_low

    @property
    def name_low(self):
        return MIDI_NAMES.get(self.note_low, str(self.note_low))

    @property
    def name_high(self):
        return MIDI_NAMES.get(self.note_high, str(self.note_high))

    def clean(self):
        super().clean()
        if self.note_low == self.note_high:
            raise ValidationError("Transition notes must be distinct.")

    def save(self, *args, **kwargs):
        if self.note_low > self.note_high:
            self.note_low, self.note_high = self.note_high, self.note_low
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name_low} -> {self.name_high}"


class TransitionSession(models.Model):
    profile = models.ForeignKey(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="transition_sessions",
    )
    date = models.DateField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.profile} - {self.date} - transitions"


class TransitionLog(models.Model):
    session = models.ForeignKey(
        TransitionSession,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    transition_practice = models.ForeignKey(
        TransitionPractice,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    exercise_id = models.CharField(max_length=10)
    rating = models.PositiveSmallIntegerField()
    achieved_tempo = models.PositiveSmallIntegerField(null=True, blank=True)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["logged_at"]

    def __str__(self):
        return f"{self.transition_practice} - {self.exercise_id} - {self.rating}/5"
