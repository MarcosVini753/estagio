import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("computers", "0001_initial"),
        ("operations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Occurrence",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reported_by_reference", models.CharField(max_length=100)),
                ("description", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "Aberta"),
                            ("IN_REVIEW", "Em análise"),
                            ("RESOLVED", "Resolvida"),
                            ("CANCELLED", "Cancelada"),
                        ],
                        default="OPEN",
                        max_length=16,
                    ),
                ),
                (
                    "resolved_by_profile",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("ROOM_USER", "Usuário da Sala"),
                            ("INTERN", "Estagiário"),
                            ("LIBRARY_SUPERVISOR", "Supervisor da Biblioteca"),
                            ("SYSTEM_ADMIN", "Administrador do Sistema"),
                        ],
                        max_length=32,
                    ),
                ),
                ("resolution_notes", models.TextField(blank=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "allocation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="occurrences",
                        to="operations.computerallocation",
                    ),
                ),
                (
                    "computer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="occurrences",
                        to="computers.computer",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="occurrences",
                        to="operations.usesession",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        )
    ]
