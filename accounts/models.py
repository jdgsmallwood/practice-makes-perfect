from django.contrib.auth.models import User
from django.db import models


class Instrument(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    midi_low = models.PositiveSmallIntegerField(default=60)
    midi_high = models.PositiveSmallIntegerField(default=96)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profiles")
    name = models.CharField(max_length=100)
    instrument = models.ForeignKey(
        Instrument,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        instrument_name = self.instrument.name if self.instrument else "No instrument"
        return f"{self.name} ({instrument_name})"
