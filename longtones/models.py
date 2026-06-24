from django.db import models

from .utils import FOCUS_CHOICES


class LongToneSession(models.Model):
    profile      = models.ForeignKey("accounts.Profile", on_delete=models.CASCADE,
                                     related_name="long_tone_sessions")
    date         = models.DateField()
    focus        = models.CharField(max_length=20, choices=FOCUS_CHOICES)
    use_drone    = models.BooleanField(default=True)
    started_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.profile} — {self.date} — {self.get_focus_display()}"


class LongToneLog(models.Model):
    session   = models.ForeignKey(LongToneSession, on_delete=models.CASCADE,
                                   related_name="logs")
    midi      = models.PositiveSmallIntegerField()
    note_name = models.CharField(max_length=8)
    rating    = models.PositiveSmallIntegerField()
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["logged_at"]

    def __str__(self):
        return f"{self.note_name} — {self.rating}/5"
