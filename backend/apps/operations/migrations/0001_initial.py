import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("computers", "0001_initial"),
        ("configuration", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Reservation",
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
                ("user_reference", models.CharField(db_index=True, max_length=100)),
                ("starts_at", models.DateTimeField()),
                ("ends_at", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("CONFIRMED", "Confirmada"),
                            ("CANCELLED", "Cancelada"),
                            ("USED", "Utilizada"),
                            ("NO_SHOW", "Não compareceu"),
                            ("INVALIDATED", "Invalidada"),
                        ],
                        default="CONFIRMED",
                        max_length=16,
                    ),
                ),
                (
                    "created_by_profile",
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
                (
                    "cancelled_by_profile",
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
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("cancellation_reason", models.TextField(blank=True)),
                (
                    "computer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reservations",
                        to="computers.computer",
                    ),
                ),
            ],
            options={
                "ordering": ["starts_at"],
                "indexes": [
                    models.Index(
                        fields=["computer", "starts_at", "ends_at"],
                        name="resv_comp_interval_idx",
                    ),
                    models.Index(
                        fields=["user_reference", "starts_at", "ends_at"],
                        name="resv_user_interval_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="UseSession",
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
                ("user_reference", models.CharField(db_index=True, max_length=100)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Ativa"),
                            ("FINISHED", "Finalizada"),
                            ("CANCELLED", "Cancelada"),
                        ],
                        default="ACTIVE",
                        max_length=16,
                    ),
                ),
                (
                    "entry_recorded_by_profile",
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
                (
                    "exit_recorded_by_profile",
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
                (
                    "reservation",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="use_session",
                        to="operations.reservation",
                    ),
                ),
                (
                    "start_shift",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="use_sessions",
                        to="configuration.shift",
                    ),
                ),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="ComputerAllocation",
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
                ("sequence", models.PositiveSmallIntegerField()),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                (
                    "end_reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("SWITCH", "Troca de computador"),
                            ("SESSION_FINISHED", "Sessão encerrada"),
                            ("ADMIN_CORRECTION", "Correção administrativa"),
                            ("CANCELLED", "Cancelada"),
                        ],
                        max_length=32,
                    ),
                ),
                ("switch_reason", models.TextField(blank=True)),
                (
                    "computer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="allocations",
                        to="computers.computer",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="allocations",
                        to="operations.usesession",
                    ),
                ),
            ],
            options={"ordering": ["session_id", "sequence"]},
        ),
        migrations.AddConstraint(
            model_name="reservation",
            constraint=models.CheckConstraint(
                condition=Q(("starts_at__lt", F("ends_at"))),
                name="reservation_start_before_end",
            ),
        ),
        migrations.AddConstraint(
            model_name="usesession",
            constraint=models.UniqueConstraint(
                condition=Q(("status", "ACTIVE")),
                fields=("user_reference",),
                name="one_active_session_per_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="usesession",
            constraint=models.CheckConstraint(
                condition=Q(
                    ("ended_at__isnull", True),
                    ("ended_at__gte", F("started_at")),
                    _connector="OR",
                ),
                name="session_end_not_before_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="computerallocation",
            constraint=models.UniqueConstraint(
                fields=("session", "sequence"), name="unique_allocation_sequence"
            ),
        ),
        migrations.AddConstraint(
            model_name="computerallocation",
            constraint=models.UniqueConstraint(
                condition=Q(("ended_at__isnull", True)),
                fields=("computer",),
                name="one_active_allocation_per_computer",
            ),
        ),
        migrations.AddConstraint(
            model_name="computerallocation",
            constraint=models.UniqueConstraint(
                condition=Q(("ended_at__isnull", True)),
                fields=("session",),
                name="one_active_allocation_per_session",
            ),
        ),
        migrations.AddConstraint(
            model_name="computerallocation",
            constraint=models.CheckConstraint(
                condition=Q(
                    ("ended_at__isnull", True),
                    ("ended_at__gte", F("started_at")),
                    _connector="OR",
                ),
                name="allocation_end_not_before_start",
            ),
        ),
    ]
