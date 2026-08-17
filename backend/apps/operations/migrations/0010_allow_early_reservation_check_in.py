from datetime import timedelta

from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0009_remove_reservation_invalidated_at_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="usesession",
            name="session_start_not_early",
        ),
        migrations.AddConstraint(
            model_name="usesession",
            constraint=models.CheckConstraint(
                condition=(
                    Q(
                        reservation__isnull=True,
                        started_at__gte=F("planned_starts_at"),
                    )
                    | Q(
                        reservation__isnull=False,
                        started_at__gte=(F("planned_starts_at") - timedelta(minutes=3)),
                    )
                ),
                name="session_start_within_check_in_window",
            ),
        ),
    ]
