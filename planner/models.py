from django.db import models


class PracticeSession(models.Model):
    profile = models.ForeignKey(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="practice_sessions",
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    total_minutes_planned = models.PositiveSmallIntegerField()
    # ordered list of category slugs as originally planned
    categories_json = models.JSONField()
    # [{category, label, minutes, start_url, item_count, completed_at}]
    sections_json = models.JSONField(default=list)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        name = self.profile.name if self.profile else "no profile"
        return f"{name} session @ {self.started_at:%Y-%m-%d %H:%M}"
