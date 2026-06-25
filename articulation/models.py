from django.db import models

from .utils import TRACK_CHOICES


class ArticulationSession(models.Model):
    profile      = models.ForeignKey("accounts.Profile", on_delete=models.CASCADE,
                                     related_name="articulation_sessions")
    date         = models.DateField()
    track        = models.CharField(max_length=20, choices=TRACK_CHOICES)
    started_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.profile} — {self.date} — {self.get_track_display()}"


class ArticulationLog(models.Model):
    session     = models.ForeignKey(ArticulationSession, on_delete=models.CASCADE,
                                    related_name="logs")
    exercise_id = models.CharField(max_length=10)
    rating      = models.PositiveSmallIntegerField()
    logged_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["logged_at"]

    def __str__(self):
        return f"{self.exercise_id} — {self.rating}/5"
