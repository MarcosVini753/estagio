from django.db import models

from apps.core.enums import DemoProfile


class AuditEvent(models.Model):
    actor_profile = models.CharField(max_length=32, choices=DemoProfile.choices)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["entity_type", "entity_id", "created_at"],
                name="audit_entity_created_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.action} - {self.entity_type}:{self.entity_id}"
