from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("scales", "0004_scalepractice_notes"),
    ]

    operations = [
        migrations.RemoveField(model_name="scalepractice", name="sm2_enabled"),
        migrations.RemoveField(model_name="scalepractice", name="ease_factor"),
        migrations.RemoveField(model_name="scalepractice", name="interval_days"),
        migrations.RemoveField(model_name="scalepractice", name="next_review_at"),
        migrations.RemoveField(model_name="scalelog", name="interval_before"),
        migrations.RemoveField(model_name="scalelog", name="interval_after"),
    ]
