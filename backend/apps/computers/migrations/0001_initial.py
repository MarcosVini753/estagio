from django.db import migrations, models
from django.db.models import F, Q
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Computer",
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
                ("code", models.CharField(max_length=32, unique=True)),
                (
                    "asset_number",
                    models.CharField(blank=True, max_length=64, null=True, unique=True),
                ),
                ("description", models.CharField(blank=True, max_length=255)),
                (
                    "operational_state",
                    models.CharField(
                        choices=[
                            ("AVAILABLE", "Disponível"),
                            ("MAINTENANCE", "Em manutenção"),
                            ("INACTIVE", "Inativo"),
                        ],
                        default="AVAILABLE",
                        max_length=16,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.CreateModel(
            name="ComputerOperationalStateChange",
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
                (
                    "previous_state",
                    models.CharField(
                        choices=[
                            ("AVAILABLE", "Disponível"),
                            ("MAINTENANCE", "Em manutenção"),
                            ("INACTIVE", "Inativo"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "new_state",
                    models.CharField(
                        choices=[
                            ("AVAILABLE", "Disponível"),
                            ("MAINTENANCE", "Em manutenção"),
                            ("INACTIVE", "Inativo"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "actor_profile",
                    models.CharField(
                        choices=[
                            ("ROOM_USER", "Usuário da Sala"),
                            ("INTERN", "Estagiário"),
                            ("LIBRARY_SUPERVISOR", "Supervisor da Biblioteca"),
                            ("SYSTEM_ADMIN", "Administrador do Sistema"),
                        ],
                        max_length=32,
                    ),
                ),
                ("reason", models.TextField(blank=True)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "computer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="operational_state_changes",
                        to="computers.computer",
                    ),
                ),
            ],
            options={"ordering": ["-changed_at"]},
        ),
        migrations.AddConstraint(
            model_name="computeroperationalstatechange",
            constraint=models.CheckConstraint(
                condition=~Q(("previous_state", F("new_state"))),
                name="computer_state_change_must_change",
            ),
        ),
    ]
