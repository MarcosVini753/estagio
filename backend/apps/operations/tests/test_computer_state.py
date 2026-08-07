from datetime import datetime, time, timedelta
from threading import Barrier, Event, Thread
from unittest.mock import patch

from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.audit.models import AuditEvent
from apps.computers.models import Computer, ComputerOperationalStateChange
from apps.configuration.models import BookingPolicy, OperatingSchedule, Weekday
from apps.configuration.tests.factories import create_operating_schedule
from apps.core.api.errors import ReservationUnavailable, UsageSessionConflict
from apps.operations.models import ComputerAllocation, Reservation, UseSession
from apps.operations.services import (
    create_reservation as reserve_computer,
)
from apps.operations.services import (
    start_usage_session,
    switch_computer,
)
from apps.operations.services.computer_state import change_computer_operational_state

from .factories import create_reservation, create_use_session


class ComputerOperationalStateAPITest(APITestCase):
    def setUp(self):
        self.now = timezone.now()
        self.source = Computer.objects.create(code="PC-01")
        self.destination = Computer.objects.create(code="PC-02")
        self.client.post(
            "/api/demo/select-profile/",
            {"profile": "ROOM_MONITOR"},
            format="json",
        )

    def change_state(self, state="MAINTENANCE", reason="Falha no monitor"):
        with patch(
            "apps.operations.services.computer_state.timezone.now",
            return_value=self.now,
        ):
            return self.client.patch(
                f"/api/computers/{self.source.pk}/operational-state/",
                {"operational_state": state, "reason": reason},
                format="json",
            )

    def create_active_session(self):
        session = create_use_session(
            user_reference="aluno-em-uso",
            started_at=self.now - timedelta(minutes=10),
            planned_starts_at=self.now - timedelta(minutes=10),
            planned_ends_at=self.now + timedelta(hours=1),
            exit_deadline_at=self.now + timedelta(hours=1, minutes=3),
            entry_recorded_by_profile="ROOM_MONITOR",
        )
        allocation = ComputerAllocation.objects.create(
            session=session,
            computer=self.source,
            sequence=1,
            started_at=session.started_at,
        )
        return session, allocation

    def create_future_reservation(self):
        return create_reservation(
            user_reference="aluno-reservado",
            computer=self.source,
            starts_at=self.now + timedelta(hours=2),
            ends_at=self.now + timedelta(hours=3),
            created_by_profile="ROOM_USER",
        )

    def test_unavailable_state_without_impacts_only_changes_computer(self):
        response = self.change_state()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["computer"]["operational_state"], "MAINTENANCE")
        self.assertIsNone(response.data["impact"]["active_session"])
        self.assertEqual(response.data["impact"]["reservations"]["reallocated"], [])
        self.assertEqual(response.data["impact"]["reservations"]["cancelled"], [])
        self.assertTrue(
            ComputerOperationalStateChange.objects.filter(computer=self.source).exists()
        )

    def test_active_session_is_transferred_to_available_computer(self):
        session, source_allocation = self.create_active_session()

        response = self.change_state()

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        source_allocation.refresh_from_db()
        destination_allocation = session.allocations.get(ended_at__isnull=True)
        self.assertEqual(session.status, UseSession.Status.ACTIVE)
        self.assertEqual(
            source_allocation.end_reason,
            ComputerAllocation.EndReason.COMPUTER_UNAVAILABLE,
        )
        self.assertEqual(destination_allocation.computer, self.destination)
        self.assertEqual(
            response.data["impact"]["active_session"]["action"], "REALLOCATED"
        )

    def test_active_session_is_finished_when_no_replacement_exists(self):
        self.destination.operational_state = Computer.OperationalState.MAINTENANCE
        self.destination.save(update_fields=["operational_state", "updated_at"])
        session, allocation = self.create_active_session()

        response = self.change_state(state="INACTIVE")

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        allocation.refresh_from_db()
        self.assertEqual(session.status, UseSession.Status.FINISHED)
        self.assertEqual(session.ended_at, self.now)
        self.assertEqual(
            allocation.end_reason,
            ComputerAllocation.EndReason.COMPUTER_UNAVAILABLE,
        )
        self.assertEqual(
            response.data["impact"]["active_session"]["action"], "FINISHED"
        )

    def test_future_reservation_is_reallocated_and_audited(self):
        reservation = self.create_future_reservation()

        response = self.change_state()

        self.assertEqual(response.status_code, 200)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        self.assertEqual(reservation.computer, self.destination)
        self.assertEqual(
            response.data["impact"]["reservations"]["reallocated"][0]["reservation_id"],
            reservation.pk,
        )
        event = AuditEvent.objects.get(action="RESERVATION_REALLOCATED")
        self.assertEqual(event.old_values["computer_id"], self.source.pk)
        self.assertEqual(event.new_values["computer_id"], self.destination.pk)

    def test_future_reservation_is_cancelled_when_no_replacement_exists(self):
        self.destination.operational_state = Computer.OperationalState.INACTIVE
        self.destination.save(update_fields=["operational_state", "updated_at"])
        reservation = self.create_future_reservation()

        response = self.change_state()

        self.assertEqual(response.status_code, 200)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)
        self.assertEqual(reservation.cancelled_by_profile, "ROOM_MONITOR")
        self.assertEqual(reservation.cancelled_at, self.now)
        self.assertEqual(
            response.data["impact"]["reservations"]["cancelled"],
            [{"reservation_id": reservation.pk}],
        )

    def test_reservation_inside_check_in_window_is_still_reallocated(self):
        reservation = create_reservation(
            user_reference="aluno-no-check-in",
            computer=self.source,
            starts_at=self.now - timedelta(minutes=1),
            ends_at=self.now + timedelta(minutes=29),
            created_by_profile="ROOM_USER",
        )

        response = self.change_state()

        self.assertEqual(response.status_code, 200)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        self.assertEqual(reservation.computer, self.destination)

    def test_each_reservation_interval_is_resolved_independently(self):
        first = self.create_future_reservation()
        second = create_reservation(
            user_reference="aluno-reservado-2",
            computer=self.source,
            starts_at=self.now + timedelta(hours=4),
            ends_at=self.now + timedelta(hours=5),
            created_by_profile="ROOM_USER",
        )
        create_reservation(
            user_reference="bloqueio-destino",
            computer=self.destination,
            starts_at=first.starts_at,
            ends_at=first.ends_at,
            created_by_profile="ROOM_USER",
        )

        response = self.change_state()

        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.status, Reservation.Status.CANCELLED)
        self.assertEqual(second.status, Reservation.Status.CONFIRMED)
        self.assertEqual(second.computer, self.destination)
        self.assertEqual(
            response.data["impact"]["reservations"]["cancelled"],
            [{"reservation_id": first.pk}],
        )
        self.assertEqual(
            response.data["impact"]["reservations"]["reallocated"][0]["reservation_id"],
            second.pk,
        )

    def test_planned_session_conflict_prevents_reservation_reallocation(self):
        reservation = self.create_future_reservation()
        session = create_use_session(
            user_reference="aluno-no-destino",
            started_at=self.now,
            planned_starts_at=self.now,
            planned_ends_at=self.now + timedelta(hours=4),
            exit_deadline_at=self.now + timedelta(hours=4, minutes=3),
            entry_recorded_by_profile="ROOM_MONITOR",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=self.destination,
            sequence=1,
            started_at=self.now,
        )

        response = self.change_state()

        self.assertEqual(response.status_code, 200)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)

    def test_transition_between_unavailable_states_does_not_reconcile_impacts(self):
        self.source.operational_state = Computer.OperationalState.MAINTENANCE
        self.source.save(update_fields=["operational_state", "updated_at"])
        reservation = self.create_future_reservation()

        response = self.change_state(state="INACTIVE")

        self.assertEqual(response.status_code, 200)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        self.assertEqual(reservation.computer, self.source)
        self.assertEqual(response.data["impact"]["reservations"]["reallocated"], [])

    def test_failure_after_reconciliation_rolls_back_everything(self):
        reservation = self.create_future_reservation()

        with (
            patch(
                "apps.operations.services.computer_state.record_operational_state_change",
                side_effect=RuntimeError("falha simulada"),
            ),
            self.assertRaises(RuntimeError),
        ):
            self.change_state()

        self.source.refresh_from_db()
        reservation.refresh_from_db()
        self.assertEqual(
            self.source.operational_state, Computer.OperationalState.AVAILABLE
        )
        self.assertEqual(reservation.computer, self.source)
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        self.assertFalse(AuditEvent.objects.exists())


class ComputerOperationalStateConcurrencyTest(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)
        local_zone = timezone.get_current_timezone()
        self.current = timezone.make_aware(
            datetime.combine(self.today, time(8)),
            local_zone,
        )
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(13))] for weekday in Weekday.values
            },
        )
        BookingPolicy.objects.create(valid_from=self.today - timedelta(days=1))

    def _hold_change_before_commit(self, source, reached, release, results):
        original_create = AuditEvent.objects.create

        def hold_final_audit(*args, **kwargs):
            if kwargs.get("action") == "COMPUTER_OPERATIONAL_STATE_CHANGED":
                reached.set()
                release.wait(timeout=5)
            return original_create(*args, **kwargs)

        close_old_connections()
        try:
            with patch(
                "apps.operations.services.computer_state.AuditEvent.objects.create",
                side_effect=hold_final_audit,
            ):
                change_computer_operational_state(
                    computer_id=source.pk,
                    new_state=Computer.OperationalState.MAINTENANCE,
                    actor_profile="ROOM_MONITOR",
                    reason="Teste concorrente.",
                    now=self.current,
                )
            results.append("maintenance")
        finally:
            connections.close_all()

    def test_maintenance_and_new_reservation_have_consistent_ordering(self):
        source = Computer.objects.create(code="PC-01")
        reached = Event()
        release = Event()
        reservation_started = Event()
        results = []

        def reserve():
            close_old_connections()
            try:
                reservation_started.set()
                reserve_computer(
                    computer_id=source.pk,
                    starts_at=self.current + timedelta(days=1),
                    slot_count=4,
                    user_reference="aluno-concorrente",
                    affiliation_type="STUDENT",
                    institutional_unit="Sistemas de Informação",
                    created_by_profile="ROOM_USER",
                    now=self.current,
                )
                results.append("reservation")
            except ReservationUnavailable:
                results.append("rejected")
            finally:
                connections.close_all()

        change_thread = Thread(
            target=self._hold_change_before_commit,
            args=(source, reached, release, results),
        )
        change_thread.start()
        self.assertTrue(reached.wait(timeout=5))
        reservation_thread = Thread(target=reserve)
        reservation_thread.start()
        self.assertTrue(reservation_started.wait(timeout=5))
        reservation_thread.join(timeout=0.2)
        reservation_was_waiting = reservation_thread.is_alive()

        release.set()
        change_thread.join(timeout=5)
        reservation_thread.join(timeout=5)

        self.assertTrue(reservation_was_waiting, results)
        self.assertCountEqual(results, ["maintenance", "rejected"])
        self.assertFalse(Reservation.objects.exists())

    def test_maintenance_and_new_session_have_consistent_ordering(self):
        source = Computer.objects.create(code="PC-01")
        reached = Event()
        release = Event()
        session_started = Event()
        results = []

        def enter():
            close_old_connections()
            try:
                session_started.set()
                start_usage_session(
                    computer_id=source.pk,
                    slot_count=4,
                    actor_profile="ROOM_USER",
                    actor_reference="aluno-concorrente",
                    affiliation_type="STUDENT",
                    institutional_unit="Sistemas de Informação",
                    now=self.current,
                )
                results.append("session")
            except UsageSessionConflict:
                results.append("rejected")
            finally:
                connections.close_all()

        change_thread = Thread(
            target=self._hold_change_before_commit,
            args=(source, reached, release, results),
        )
        change_thread.start()
        self.assertTrue(reached.wait(timeout=5))
        session_thread = Thread(target=enter)
        session_thread.start()
        self.assertTrue(session_started.wait(timeout=5))
        session_thread.join(timeout=0.2)
        session_was_waiting = session_thread.is_alive()

        release.set()
        change_thread.join(timeout=5)
        session_thread.join(timeout=5)

        self.assertTrue(session_was_waiting, results)
        self.assertCountEqual(results, ["maintenance", "rejected"])
        self.assertFalse(UseSession.objects.exists())

    def test_two_maintenances_do_not_reallocate_to_same_destination(self):
        first_source = Computer.objects.create(code="PC-01")
        second_source = Computer.objects.create(code="PC-02")
        destination = Computer.objects.create(code="PC-03")
        starts_at = self.current + timedelta(days=1)
        first = create_reservation(
            user_reference="aluno-1",
            computer=first_source,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            created_by_profile="ROOM_USER",
        )
        second = create_reservation(
            user_reference="aluno-2",
            computer=second_source,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            created_by_profile="ROOM_USER",
        )
        barrier = Barrier(2)
        results = []

        def change(source):
            close_old_connections()
            try:
                barrier.wait()
                change_computer_operational_state(
                    computer_id=source.pk,
                    new_state=Computer.OperationalState.MAINTENANCE,
                    actor_profile="ROOM_MONITOR",
                    reason="Teste concorrente.",
                    now=self.current,
                )
                results.append("changed")
            finally:
                connections.close_all()

        first_thread = Thread(target=change, args=(first_source,))
        second_thread = Thread(target=change, args=(second_source,))
        first_thread.start()
        second_thread.start()
        first_thread.join(timeout=5)
        second_thread.join(timeout=5)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertCountEqual(results, ["changed", "changed"])
        self.assertEqual(
            Reservation.objects.filter(
                computer=destination,
                status=Reservation.Status.CONFIRMED,
            ).count(),
            1,
        )
        self.assertCountEqual(
            [first.status, second.status],
            [Reservation.Status.CONFIRMED, Reservation.Status.CANCELLED],
        )

    def test_maintenance_and_switch_do_not_deadlock(self):
        source = Computer.objects.create(code="PC-01")
        destination = Computer.objects.create(code="PC-02")
        session = create_use_session(
            user_reference="aluno-trocando",
            started_at=self.current,
            planned_starts_at=self.current,
            planned_ends_at=self.current + timedelta(hours=1),
            exit_deadline_at=self.current + timedelta(hours=1, minutes=3),
            entry_recorded_by_profile="ROOM_USER",
        )
        ComputerAllocation.objects.create(
            session=session,
            computer=source,
            sequence=1,
            started_at=self.current,
        )
        barrier = Barrier(2)
        results = []

        def maintain():
            close_old_connections()
            try:
                barrier.wait()
                change_computer_operational_state(
                    computer_id=source.pk,
                    new_state=Computer.OperationalState.MAINTENANCE,
                    actor_profile="ROOM_MONITOR",
                    reason="Teste concorrente.",
                    now=self.current,
                )
                results.append("maintenance")
            finally:
                connections.close_all()

        def switch():
            close_old_connections()
            try:
                barrier.wait()
                switch_computer(
                    session_id=session.pk,
                    computer_id=destination.pk,
                    actor_profile="ROOM_USER",
                    actor_reference="aluno-trocando",
                    now=self.current + timedelta(minutes=15),
                )
                results.append("switch")
            except UsageSessionConflict:
                results.append("conflict")
            finally:
                connections.close_all()

        maintenance_thread = Thread(target=maintain)
        switch_thread = Thread(target=switch)
        maintenance_thread.start()
        switch_thread.start()
        maintenance_thread.join(timeout=10)
        switch_thread.join(timeout=10)

        self.assertFalse(maintenance_thread.is_alive())
        self.assertFalse(switch_thread.is_alive())
        self.assertEqual(len(results), 2)
        session.refresh_from_db()
        self.assertEqual(session.status, UseSession.Status.ACTIVE)
        self.assertEqual(session.allocations.filter(ended_at__isnull=True).count(), 1)
