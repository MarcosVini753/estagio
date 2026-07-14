from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
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
                ("action", models.CharField(max_length=100)),
                ("entity_type", models.CharField(max_length=100)),
                ("entity_id", models.CharField(max_length=100)),
                ("old_values", models.JSONField(blank=True, default=dict)),
                ("new_values", models.JSONField(blank=True, default=dict)),
                ("reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["entity_type", "entity_id", "created_at"],
                        name="audit_entity_created_idx",
                    )
                ],
            },
        )
    ]
