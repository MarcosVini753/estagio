from django.db import models
from django.db.models import F, Q

from apps.core.enums import DemoProfile
from apps.core.models import TimeStampedModel


class Computer(TimeStampedModel):
    class OperationalState(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Disponível"
        MAINTENANCE = "MAINTENANCE", "Em manutenção"
        INACTIVE = "INACTIVE", "Inativo"

    code = models.CharField(max_length=32, unique=True)
    asset_number = models.CharField(max_length=64, unique=True, null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    operational_state = models.CharField(
        max_length=16,
        choices=OperationalState.choices,
        default=OperationalState.AVAILABLE,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class ComputerOperationalStateChange(models.Model):
    computer = models.ForeignKey(
        Computer,
        on_delete=models.CASCADE,
        related_name="operational_state_changes",
    )
    previous_state = models.CharField(
        max_length=16, choices=Computer.OperationalState.choices
    )
    new_state = models.CharField(
        max_length=16, choices=Computer.OperationalState.choices
    )
    actor_profile = models.CharField(max_length=32, choices=DemoProfile.choices)
    reason = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(previous_state=F("new_state")),
                name="computer_state_change_must_change",
            )
        ]

    def __str__(self) -> str:
        return f"{self.computer}: {self.previous_state} → {self.new_state}"
