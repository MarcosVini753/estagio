from importlib import import_module

from django.apps import apps
from django.test import TestCase

from apps.audit.models import AuditEvent
from apps.computers.models import Computer, ComputerOperationalStateChange
from apps.occurrences.models import Occurrence


class RoomMonitorProfileMigrationTest(TestCase):
    def test_persisted_intern_profiles_are_renamed(self):
        computer = Computer.objects.create(code="PC-PROFILE-MIGRATION")
        change = ComputerOperationalStateChange.objects.create(
            computer=computer,
            previous_state=Computer.OperationalState.AVAILABLE,
            new_state=Computer.OperationalState.MAINTENANCE,
            actor_profile="INTERN",
            reason="Histórico legado.",
        )
        event = AuditEvent.objects.create(
            actor_profile="INTERN",
            action="LEGACY_EVENT",
            entity_type="Computer",
            entity_id=str(computer.pk),
        )
        occurrence = Occurrence.objects.create(
            reported_by_reference="demo-user",
            description="Ocorrência legada.",
            resolved_by_profile="INTERN",
        )

        import_module(
            "apps.audit.migrations.0002_alter_auditevent_actor_profile"
        ).rename_profile(apps, None)
        import_module(
            "apps.computers.migrations."
            "0002_alter_computeroperationalstatechange_actor_profile"
        ).rename_profile(apps, None)
        import_module(
            "apps.occurrences.migrations.0002_alter_occurrence_resolved_by_profile"
        ).rename_profile(apps, None)

        change.refresh_from_db()
        event.refresh_from_db()
        occurrence.refresh_from_db()
        self.assertEqual(change.actor_profile, "ROOM_MONITOR")
        self.assertEqual(event.actor_profile, "ROOM_MONITOR")
        self.assertEqual(occurrence.resolved_by_profile, "ROOM_MONITOR")
