from django.db import models

from apps.computers.models import Computer
from apps.core.enums import DemoProfile
from apps.core.models import TimeStampedModel
from apps.operations.models import ComputerAllocation, UseSession


class Occurrence(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Aberta"
        IN_REVIEW = "IN_REVIEW", "Em análise"
        RESOLVED = "RESOLVED", "Resolvida"
        CANCELLED = "CANCELLED", "Cancelada"

    reported_by_reference = models.CharField(max_length=100)
    computer = models.ForeignKey(
        Computer,
        on_delete=models.SET_NULL,
        related_name="occurrences",
        null=True,
        blank=True,
    )
    session = models.ForeignKey(
        UseSession,
        on_delete=models.SET_NULL,
        related_name="occurrences",
        null=True,
        blank=True,
    )
    allocation = models.ForeignKey(
        ComputerAllocation,
        on_delete=models.SET_NULL,
        related_name="occurrences",
        null=True,
        blank=True,
    )
    description = models.TextField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN
    )
    resolved_by_profile = models.CharField(
        max_length=32, choices=DemoProfile.choices, blank=True
    )
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Ocorrência {self.pk} - {self.get_status_display()}"
