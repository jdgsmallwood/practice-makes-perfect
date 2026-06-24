from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    INSTRUMENT_CHOICES = [
        ("flute", "Flute"),
        ("piccolo", "Piccolo"),
        ("alto_flute", "Alto Flute"),
        ("bass_flute", "Bass Flute"),
        ("clarinet", "Clarinet"),
        ("oboe", "Oboe"),
        ("saxophone", "Saxophone"),
        ("violin", "Violin"),
        ("piano", "Piano"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profiles")
    name = models.CharField(max_length=100)
    instrument = models.CharField(max_length=20, choices=INSTRUMENT_CHOICES, default="flute")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_instrument_display()})"
