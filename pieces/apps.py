from django.apps import AppConfig
from django.db.backends.signals import connection_created


def _activate_wal(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        connection.cursor().execute("PRAGMA journal_mode=WAL;")


class PiecesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pieces"

    def ready(self):
        connection_created.connect(_activate_wal)
