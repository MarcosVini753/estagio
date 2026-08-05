import uuid
from datetime import date

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Func, Q, Value

from apps.core.enums import DemoProfile
from apps.core.models import TimeStampedModel


class Weekday(models.IntegerChoices):
    MONDAY = 0, "Segunda-feira"
    TUESDAY = 1, "Terça-feira"
    WEDNESDAY = 2, "Quarta-feira"
    THURSDAY = 3, "Quinta-feira"
    FRIDAY = 4, "Sexta-feira"
    SATURDAY = 5, "Sábado"
    SUNDAY = 6, "Domingo"


class Shift(TimeStampedModel):
    series_key = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
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


class OperatingSchedule(TimeStampedModel):
    class ScheduleType(models.TextChoices):
        REGULAR = "REGULAR", "Regular"
        TEMPORARY = "TEMPORARY", "Temporário"

    series_key = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    name = models.CharField(max_length=120)
    schedule_type = models.CharField(max_length=16, choices=ScheduleType.choices)
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by_profile = models.CharField(max_length=32, choices=DemoProfile.choices)

    class Meta:
        ordering = ["-valid_from", "-created_at"]
        indexes = [
            models.Index(
                fields=["schedule_type", "is_active", "valid_from", "valid_until"],
                name="op_sched_validity_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_until__isnull=True)
                | Q(valid_until__gte=F("valid_from")),
                name="operating_schedule_valid_period",
            ),
            models.CheckConstraint(
                condition=Q(schedule_type="REGULAR") | Q(valid_until__isnull=False),
                name="temporary_schedule_requires_end",
            ),
            ExclusionConstraint(
                name="operating_schedule_no_same_type_overlap",
                expressions=[
                    ("schedule_type", RangeOperators.EQUAL),
                    (
                        Func(
                            F("valid_from"),
                            F("valid_until"),
                            Value("[]"),
                            function="DATERANGE",
                            output_field=DateRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(is_active=True),
            ),
        ]

    def clean(self):
        super().clean()
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValidationError(
                {"valid_until": "A validade final não pode anteceder a inicial."}
            )
        if (
            self.schedule_type == self.ScheduleType.TEMPORARY
            and self.valid_until is None
        ):
            raise ValidationError(
                {"valid_until": "Horário temporário exige uma data final."}
            )

    def __str__(self) -> str:
        return self.name


class OperatingScheduleDay(TimeStampedModel):
    schedule = models.ForeignKey(
        OperatingSchedule,
        on_delete=models.CASCADE,
        related_name="days",
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    is_open = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday"]
        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "weekday"],
                name="unique_weekday_per_operating_schedule",
            )
        ]

    def clean(self):
        super().clean()
        if self.pk and not self.is_open and self.windows.exists():
            raise ValidationError("Dia fechado não pode possuir janelas.")

    def __str__(self) -> str:
        return f"{self.schedule} - {self.get_weekday_display()}"


class OperatingWindow(TimeStampedModel):
    schedule_day = models.ForeignKey(
        OperatingScheduleDay,
        on_delete=models.CASCADE,
        related_name="windows",
    )
    opens_at = models.TimeField()
    closes_at = models.TimeField()
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "opens_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(opens_at__lt=F("closes_at")),
                name="operating_window_open_before_close",
            )
        ]

    def clean(self):
        super().clean()
        if self.opens_at and self.closes_at and self.opens_at >= self.closes_at:
            raise ValidationError(
                {"closes_at": "O fechamento deve ser posterior à abertura."}
            )
        if self.schedule_day_id and not self.schedule_day.is_open:
            raise ValidationError("Dia fechado não pode possuir janelas.")
        if (
            self.schedule_day_id
            and self.opens_at
            and self.closes_at
            and self.schedule_day.windows.filter(
                opens_at__lt=self.closes_at,
                closes_at__gt=self.opens_at,
            )
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError("As janelas do mesmo dia não podem se sobrepor.")

    def __str__(self) -> str:
        return f"{self.schedule_day}: {self.opens_at}–{self.closes_at}"


class RoomNotice(TimeStampedModel):
    class NoticeType(models.TextChoices):
        CLOSURE = "CLOSURE", "Fechamento"
        SCHEDULE_CHANGE = "SCHEDULE_CHANGE", "Mudança de horário"
        SPECIAL_HOURS = "SPECIAL_HOURS", "Horário especial"

    notice_type = models.CharField(max_length=32, choices=NoticeType.choices)
    title = models.CharField(max_length=150)
    message = models.TextField()
    effective_from = models.DateField()
    effective_until = models.DateField()
    visible_from = models.DateTimeField()
    visible_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by_profile = models.CharField(max_length=32, choices=DemoProfile.choices)
    operating_schedule = models.ForeignKey(
        OperatingSchedule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notices",
    )
    calendar_exception = models.ForeignKey(
        CalendarException,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notices",
    )

    class Meta:
        ordering = ["-visible_from", "-created_at"]
        indexes = [
            models.Index(
                fields=["is_active", "visible_from", "visible_until"],
                name="room_notice_visibility_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(effective_until__gte=F("effective_from")),
                name="room_notice_effective_period",
            ),
            models.CheckConstraint(
                condition=Q(visible_until__isnull=True)
                | Q(visible_until__gte=F("visible_from")),
                name="room_notice_visible_period",
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.effective_from
            and self.effective_until
            and self.effective_until < self.effective_from
        ):
            raise ValidationError(
                {"effective_until": "O período efetivo do aviso é inválido."}
            )
        if (
            self.visible_from
            and self.visible_until
            and self.visible_until < self.visible_from
        ):
            raise ValidationError(
                {"visible_until": "O período de visibilidade do aviso é inválido."}
            )
        if not (self.message or "").strip():
            raise ValidationError({"message": "Informe a mensagem do aviso."})

    def __str__(self) -> str:
        return self.title


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
