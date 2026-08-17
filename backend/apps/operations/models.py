from datetime import timedelta

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.models import Deferrable, F, Func, Q, Value
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.models import BookingPolicy, Shift
from apps.core.enums import AffiliationType, DemoProfile
from apps.core.models import TimeStampedModel

from .rules import EARLY_CHECK_IN_TOLERANCE_MINUTES, SLOT_DURATION_MINUTES


class Reservation(TimeStampedModel):
    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmada"
        CANCELLED = "CANCELLED", "Cancelada"
        USED = "USED", "Utilizada"

    user_reference = models.CharField(max_length=100, db_index=True)
    affiliation_type = models.CharField(
        max_length=32,
        choices=AffiliationType.choices,
        default=AffiliationType.NOT_INFORMED,
    )
    institutional_unit = models.CharField(max_length=255, blank=True, default="")
    computer = models.ForeignKey(
        Computer, on_delete=models.PROTECT, related_name="reservations"
    )
    booking_policy = models.ForeignKey(
        BookingPolicy,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    check_in_deadline_at = models.DateTimeField()
    exit_deadline_at = models.DateTimeField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.CONFIRMED
    )
    created_by_profile = models.CharField(max_length=32, choices=DemoProfile.choices)
    cancelled_by_profile = models.CharField(
        max_length=32, choices=DemoProfile.choices, blank=True
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["starts_at"]
        indexes = [
            models.Index(
                fields=["computer", "starts_at", "ends_at"],
                name="resv_comp_interval_idx",
            ),
            models.Index(
                fields=["user_reference", "starts_at", "ends_at"],
                name="resv_user_interval_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(starts_at__lt=F("ends_at")),
                name="reservation_start_before_end",
            ),
            models.CheckConstraint(
                condition=Q(starts_at__lte=F("check_in_deadline_at")),
                name="reservation_checkin_after_start",
            ),
            models.CheckConstraint(
                condition=Q(ends_at__lte=F("exit_deadline_at")),
                name="reservation_exit_after_end",
            ),
            ExclusionConstraint(
                name="reservation_computer_no_overlap",
                expressions=[
                    ("computer", RangeOperators.EQUAL),
                    (
                        Func(
                            F("starts_at"),
                            F("ends_at"),
                            Value("[)"),
                            function="TSTZRANGE",
                            output_field=DateTimeRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(status="CONFIRMED"),
            ),
            ExclusionConstraint(
                name="reservation_user_no_overlap",
                expressions=[
                    ("user_reference", RangeOperators.EQUAL),
                    (
                        Func(
                            F("starts_at"),
                            F("ends_at"),
                            Value("[)"),
                            function="TSTZRANGE",
                            output_field=DateTimeRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(status="CONFIRMED"),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_reference} - {self.computer} - {self.starts_at}"

    @property
    def slot_count(self) -> int:
        return int(
            (self.ends_at - self.starts_at).total_seconds()
            // (SLOT_DURATION_MINUTES * 60)
        )


class UseSession(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Ativa"
        FINISHED = "FINISHED", "Finalizada"
        CANCELLED = "CANCELLED", "Cancelada"

    user_reference = models.CharField(max_length=100, db_index=True)
    affiliation_type = models.CharField(
        max_length=32,
        choices=AffiliationType.choices,
        default=AffiliationType.NOT_INFORMED,
    )
    institutional_unit = models.CharField(max_length=255, blank=True, default="")
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.SET_NULL,
        related_name="use_session",
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(default=timezone.now)
    planned_starts_at = models.DateTimeField()
    planned_ends_at = models.DateTimeField()
    exit_deadline_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    start_shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        related_name="use_sessions",
        null=True,
        blank=True,
    )
    entry_recorded_by_profile = models.CharField(
        max_length=32, choices=DemoProfile.choices
    )
    exit_recorded_by_profile = models.CharField(
        max_length=32, choices=DemoProfile.choices, blank=True
    )

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(
                condition=Q(status="ACTIVE"),
                fields=["user_reference"],
                name="one_active_session_per_user",
            ),
            models.CheckConstraint(
                condition=Q(ended_at__isnull=True) | Q(ended_at__gte=F("started_at")),
                name="session_end_not_before_start",
            ),
            models.CheckConstraint(
                condition=Q(planned_starts_at__lt=F("planned_ends_at")),
                name="session_planned_start_before_end",
            ),
            models.CheckConstraint(
                condition=Q(planned_ends_at__lte=F("exit_deadline_at")),
                name="session_exit_after_planned_end",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        reservation__isnull=True,
                        started_at__gte=F("planned_starts_at"),
                    )
                    | Q(
                        reservation__isnull=False,
                        started_at__gte=(
                            F("planned_starts_at")
                            - timedelta(minutes=EARLY_CHECK_IN_TOLERANCE_MINUTES)
                        ),
                    )
                ),
                name="session_start_within_check_in_window",
            ),
            models.CheckConstraint(
                condition=Q(started_at__lte=F("exit_deadline_at")),
                name="session_start_before_exit_deadline",
            ),
        ]

    def __str__(self) -> str:
        return f"Sessão {self.pk} - {self.user_reference}"

    @property
    def slot_count(self) -> int:
        return int(
            (self.planned_ends_at - self.planned_starts_at).total_seconds()
            // (SLOT_DURATION_MINUTES * 60)
        )


class ComputerAllocation(TimeStampedModel):
    class EndReason(models.TextChoices):
        SWITCH = "SWITCH", "Troca de computador"
        COMPUTER_UNAVAILABLE = (
            "COMPUTER_UNAVAILABLE",
            "Computador indisponível",
        )
        SESSION_FINISHED = "SESSION_FINISHED", "Sessão encerrada"
        TIME_LIMIT_REACHED = "TIME_LIMIT_REACHED", "Limite de tempo atingido"
        ADMIN_CORRECTION = "ADMIN_CORRECTION", "Correção administrativa"
        CANCELLED = "CANCELLED", "Cancelada"

    session = models.ForeignKey(
        UseSession, on_delete=models.CASCADE, related_name="allocations"
    )
    computer = models.ForeignKey(
        Computer, on_delete=models.PROTECT, related_name="allocations"
    )
    sequence = models.PositiveSmallIntegerField()
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(max_length=32, choices=EndReason.choices, blank=True)
    switch_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["session_id", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "sequence"], name="unique_allocation_sequence"
            ),
            models.UniqueConstraint(
                condition=Q(ended_at__isnull=True),
                fields=["computer"],
                name="one_active_allocation_per_computer",
            ),
            models.UniqueConstraint(
                condition=Q(ended_at__isnull=True),
                fields=["session"],
                name="one_active_allocation_per_session",
            ),
            models.CheckConstraint(
                condition=Q(ended_at__isnull=True) | Q(ended_at__gte=F("started_at")),
                name="allocation_end_not_before_start",
            ),
            ExclusionConstraint(
                name="allocation_computer_no_overlap",
                expressions=[
                    ("computer", RangeOperators.EQUAL),
                    (
                        Func(
                            F("started_at"),
                            F("ended_at"),
                            Value("[)"),
                            function="TSTZRANGE",
                            output_field=DateTimeRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                deferrable=Deferrable.DEFERRED,
            ),
        ]

    def __str__(self) -> str:
        return f"Sessão {self.session_id} / {self.computer} / #{self.sequence}"
