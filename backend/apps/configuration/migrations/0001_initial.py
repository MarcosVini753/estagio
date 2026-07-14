import datetime

import django.core.validators
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BookingPolicy",
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
                (
                    "slot_duration_minutes",
                    models.PositiveSmallIntegerField(
                        default=60,
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                (
                    "check_in_tolerance_minutes",
                    models.PositiveSmallIntegerField(
                        default=15,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "cancellation_limit_minutes",
                    models.PositiveSmallIntegerField(
                        default=0,
                        validators=[django.core.validators.MinValueValidator(0)],
                    ),
                ),
                (
                    "max_future_reservations_per_user",
                    models.PositiveSmallIntegerField(
                        default=1,
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("valid_from", models.DateField(default=datetime.date.today)),
            ],
            options={"ordering": ["-valid_from"]},
        ),
        migrations.CreateModel(
            name="CalendarException",
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
                ("date", models.DateField(unique=True)),
                (
                    "exception_type",
                    models.CharField(
                        choices=[
                            ("CLOSED", "Fechado"),
                            ("SPECIAL_HOURS", "Horário especial"),
                            ("OPTIONAL_HOLIDAY", "Ponto facultativo"),
                        ],
                        max_length=32,
                    ),
                ),
                ("opens_at", models.TimeField(blank=True, null=True)),
                ("closes_at", models.TimeField(blank=True, null=True)),
                ("description", models.CharField(blank=True, max_length=255)),
            ],
            options={"ordering": ["date"]},
        ),
        migrations.CreateModel(
            name="ReportConfiguration",
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
                (
                    "default_format",
                    models.CharField(
                        choices=[("CSV", "CSV"), ("XLSX", "Planilha"), ("PDF", "PDF")],
                        default="CSV",
                        max_length=8,
                    ),
                ),
                ("group_by_shift", models.BooleanField(default=True)),
                ("include_occurrences", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Shift",
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
                ("name", models.CharField(max_length=100)),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("valid_from", models.DateField(default=datetime.date.today)),
                ("valid_until", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["display_order", "start_time"]},
        ),
        migrations.AddConstraint(
            model_name="bookingpolicy",
            constraint=models.UniqueConstraint(
                condition=Q(("is_active", True)),
                fields=("is_active",),
                name="one_active_booking_policy",
            ),
        ),
        migrations.AddConstraint(
            model_name="reportconfiguration",
            constraint=models.UniqueConstraint(
                condition=Q(("is_active", True)),
                fields=("is_active",),
                name="one_active_report_configuration",
            ),
        ),
        migrations.AddConstraint(
            model_name="shift",
            constraint=models.CheckConstraint(
                condition=Q(("start_time__lt", F("end_time"))),
                name="shift_start_before_end",
            ),
        ),
        migrations.AddConstraint(
            model_name="shift",
            constraint=models.CheckConstraint(
                condition=Q(
                    ("valid_until__isnull", True),
                    ("valid_until__gte", F("valid_from")),
                    _connector="OR",
                ),
                name="shift_valid_period",
            ),
        ),
    ]
