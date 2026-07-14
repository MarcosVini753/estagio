from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.models import Shift
from apps.core.enums import DemoProfile
from apps.core.models import TimeStampedModel


class Reservation(TimeStampedModel):
    class Status(models.TextChoices):
        CONFIRMED = "CONFIRMED", "Confirmada"
        CANCELLED = "CANCELLED", "Cancelada"
        USED = "USED", "Utilizada"
        NO_SHOW = "NO_SHOW", "Não compareceu"
        INVALIDATED = "INVALIDATED", "Invalidada"

    user_reference = models.CharField(max_length=100, db_index=True)
    computer = models.ForeignKey(
        Computer, on_delete=models.PROTECT, related_name="reservations"
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
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
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_reference} - {self.computer} - {self.starts_at}"


class UseSession(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Ativa"
        FINISHED = "FINISHED", "Finalizada"
        CANCELLED = "CANCELLED", "Cancelada"

    user_reference = models.CharField(max_length=100, db_index=True)
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.SET_NULL,
        related_name="use_session",
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(default=timezone.now)
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
        ]

    def __str__(self) -> str:
        return f"Sessão {self.pk} - {self.user_reference}"


class ComputerAllocation(TimeStampedModel):
    class EndReason(models.TextChoices):
        SWITCH = "SWITCH", "Troca de computador"
        SESSION_FINISHED = "SESSION_FINISHED", "Sessão encerrada"
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
        ]

    def __str__(self) -> str:
        return f"Sessão {self.session_id} / {self.computer} / #{self.sequence}"
