from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0005_reservation_invalidation_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="reservation",
            name="check_in_deadline_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="reservation",
            name="exit_deadline_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="reservation",
            name="no_show_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="usesession",
            name="planned_starts_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="usesession",
            name="planned_ends_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="usesession",
            name="exit_deadline_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name="computerallocation",
            name="end_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("SWITCH", "Troca de computador"),
                    ("SESSION_FINISHED", "Sessão encerrada"),
                    ("TIME_LIMIT_REACHED", "Limite de tempo atingido"),
                    ("ADMIN_CORRECTION", "Correção administrativa"),
                    ("CANCELLED", "Cancelada"),
                ],
                max_length=32,
            ),
        ),
    ]
