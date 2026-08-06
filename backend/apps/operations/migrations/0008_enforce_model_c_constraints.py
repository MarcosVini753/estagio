from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0007_backfill_model_c_deadlines"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reservation",
            name="check_in_deadline_at",
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name="reservation",
            name="exit_deadline_at",
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name="usesession",
            name="planned_starts_at",
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name="usesession",
            name="planned_ends_at",
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name="usesession",
            name="exit_deadline_at",
            field=models.DateTimeField(),
        ),
        migrations.AddConstraint(
            model_name="reservation",
            constraint=models.CheckConstraint(
                condition=Q(starts_at__lte=F("check_in_deadline_at")),
                name="reservation_checkin_after_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="reservation",
            constraint=models.CheckConstraint(
                condition=Q(ends_at__lte=F("exit_deadline_at")),
                name="reservation_exit_after_end",
            ),
        ),
        migrations.AddConstraint(
            model_name="usesession",
            constraint=models.CheckConstraint(
                condition=Q(planned_starts_at__lt=F("planned_ends_at")),
                name="session_planned_start_before_end",
            ),
        ),
        migrations.AddConstraint(
            model_name="usesession",
            constraint=models.CheckConstraint(
                condition=Q(planned_ends_at__lte=F("exit_deadline_at")),
                name="session_exit_after_planned_end",
            ),
        ),
        migrations.AddConstraint(
            model_name="usesession",
            constraint=models.CheckConstraint(
                condition=Q(started_at__gte=F("planned_starts_at")),
                name="session_start_not_early",
            ),
        ),
        migrations.AddConstraint(
            model_name="usesession",
            constraint=models.CheckConstraint(
                condition=Q(started_at__lte=F("exit_deadline_at")),
                name="session_start_before_exit_deadline",
            ),
        ),
    ]
