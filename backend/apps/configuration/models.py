from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.core.models import TimeStampedModel


class Shift(TimeStampedModel):
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    display_order = models.PositiveSmallIntegerField(default=0)
    valid_from = models.DateField(default=date.today)
    valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=Q(start_time__lt=F("end_time")),
                name="shift_start_before_end",
            ),
            models.CheckConstraint(
                condition=Q(valid_until__isnull=True)
                | Q(valid_until__gte=F("valid_from")),
                name="shift_valid_period",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class CalendarException(TimeStampedModel):
    class ExceptionType(models.TextChoices):
        CLOSED = "CLOSED", "Fechado"
        SPECIAL_HOURS = "SPECIAL_HOURS", "Horário especial"
        OPTIONAL_HOLIDAY = "OPTIONAL_HOLIDAY", "Ponto facultativo"

    date = models.DateField(unique=True)
    exception_type = models.CharField(max_length=32, choices=ExceptionType.choices)
    opens_at = models.TimeField(null=True, blank=True)
    closes_at = models.TimeField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["date"]

    def clean(self):
        super().clean()
        if self.exception_type == self.ExceptionType.SPECIAL_HOURS:
            if not self.opens_at or not self.closes_at:
                raise ValidationError("Horário especial exige abertura e fechamento.")
            if self.opens_at >= self.closes_at:
                raise ValidationError(
                    "O horário de abertura deve anteceder o fechamento."
                )

    def __str__(self) -> str:
        return f"{self.date} - {self.get_exception_type_display()}"


class BookingPolicy(TimeStampedModel):
    slot_duration_minutes = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(1)],
    )
    check_in_tolerance_minutes = models.PositiveSmallIntegerField(
        default=15,
        validators=[MinValueValidator(0)],
    )
    cancellation_limit_minutes = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    max_future_reservations_per_user = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(default=date.today)

    class Meta:
        ordering = ["-valid_from"]
        constraints = [
            models.UniqueConstraint(
                condition=Q(is_active=True),
                fields=["is_active"],
                name="one_active_booking_policy",
            )
        ]

    def __str__(self) -> str:
        return f"Política válida desde {self.valid_from}"


class ReportConfiguration(TimeStampedModel):
    class ExportFormat(models.TextChoices):
        CSV = "CSV", "CSV"
        XLSX = "XLSX", "Planilha"
        PDF = "PDF", "PDF"

    default_format = models.CharField(
        max_length=8,
        choices=ExportFormat.choices,
        default=ExportFormat.CSV,
    )
    group_by_shift = models.BooleanField(default=True)
    include_occurrences = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                condition=Q(is_active=True),
                fields=["is_active"],
                name="one_active_report_configuration",
            )
        ]

    def __str__(self) -> str:
        return (
            "Configuração ativa de relatórios"
            if self.is_active
            else "Configuração inativa"
        )
