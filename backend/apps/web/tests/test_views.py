from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.computers.models import Computer
from apps.configuration.models import (
    BookingPolicy,
    OperatingSchedule,
    RoomNotice,
    Weekday,
)
from apps.configuration.tests.factories import create_operating_schedule
from apps.occurrences.models import Occurrence
from apps.operations.models import Reservation, UseSession
from apps.operations.tests.factories import create_reservation


class RoomUserWebTest(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)
        self.fixed_now = self.aware(self.today, time(8))
        self.computer = Computer.objects.create(
            code="PC-01",
            description="Computador 01",
            notes="Próximo à entrada",
        )
        self.other_computer = Computer.objects.create(
            code="PC-02",
            description="Computador 02",
        )
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={
                weekday: [(time(7), time(22))] for weekday in Weekday.values
            },
        )
        BookingPolicy.objects.create(
            max_future_reservations_per_user=3,
            valid_from=self.today - timedelta(days=1),
        )

    def aware(self, target_date, target_time):
        return timezone.make_aware(
            datetime.combine(target_date, target_time),
            timezone.get_current_timezone(),
        )

    def select_room_user(self):
        response = self.client.post(
            "/",
            {
                "profile": "ROOM_USER",
                "user_reference": "aluno-si-001",
                "affiliation_type": "STUDENT",
                "institutional_unit": "Sistemas de Informação",
            },
        )
        self.assertRedirects(response, "/sala/computadores/")

    def test_home_lists_four_profiles_and_requires_room_user_identity(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="ROOM_USER"')
        self.assertContains(response, 'value="ROOM_MONITOR"')
        self.assertContains(response, 'value="LIBRARY_SUPERVISOR"')
        self.assertContains(response, 'value="SYSTEM_ADMIN"')

        invalid = self.client.post("/", {"profile": "ROOM_USER"})
        self.assertEqual(invalid.status_code, 400)
        self.assertContains(invalid, "obrigatório", status_code=400)

    def test_active_notice_is_visible_before_and_after_profile_selection(self):
        RoomNotice.objects.create(
            notice_type=RoomNotice.NoticeType.SPECIAL_HOURS,
            title="Horário especial hoje",
            message="A sala encerrará mais cedo.",
            effective_from=self.today,
            effective_until=self.today,
            visible_from=timezone.now() - timedelta(hours=1),
            created_by_profile="LIBRARY_SUPERVISOR",
        )

        home = self.client.get("/")
        self.select_room_user()
        computers = self.client.get("/sala/computadores/")

        self.assertContains(home, "Horário especial hoje")
        self.assertContains(computers, "Horário especial hoje")

    def test_monitor_reaches_its_functional_area(self):
        response = self.client.post("/", {"profile": "ROOM_MONITOR"})

        self.assertRedirects(response, "/monitor/")

    def test_unmigrated_profile_reaches_pending_profile_page(self):
        response = self.client.post("/", {"profile": "SYSTEM_ADMIN"})

        self.assertRedirects(response, "/perfil-indisponivel/")
        pending = self.client.get("/perfil-indisponivel/")
        self.assertContains(pending, "Administrador do Sistema")
        self.assertContains(pending, "ainda não foi migrada")

    def test_room_user_pages_require_compatible_profile(self):
        response = self.client.get("/sala/computadores/")

        self.assertRedirects(response, "/")

        self.select_room_user()
        self.client.post("/", {"profile": "ROOM_MONITOR"})
        changed_profile = self.client.get("/sala/computadores/")
        self.assertRedirects(changed_profile, "/")

    def test_computers_render_today_tomorrow_search_and_htmx_partial(self):
        self.select_room_user()
        with patch(
            "apps.operations.availability.timezone.now",
            return_value=self.fixed_now,
        ):
            today_response = self.client.get("/sala/computadores/?day=today")
            tomorrow_response = self.client.get(
                "/sala/computadores/?day=tomorrow&q=PC-02"
            )
            partial = self.client.get(
                "/sala/computadores/?day=tomorrow",
                HTTP_HX_REQUEST="true",
                HTTP_HX_TARGET="screen-content",
            )
            detail = self.client.get(
                f"/sala/computadores/{self.computer.pk}/",
                {
                    "day": "tomorrow",
                    "starts_at": self.aware(self.tomorrow, time(9)).isoformat(),
                },
                HTTP_HX_REQUEST="true",
            )

        self.assertContains(today_response, "Computador 01")
        self.assertContains(today_response, "Hoje")
        self.assertContains(today_response, "Perfil de teste")
        self.assertNotContains(today_response, "Ambiente demonstrativo")
        self.assertNotContains(tomorrow_response, "Computador 01")
        self.assertContains(tomorrow_response, "Computador 02")
        self.assertContains(tomorrow_response, "horários disponíveis")
        self.assertContains(partial, 'id="screen-content"')
        self.assertNotContains(partial, "<!doctype html>")
        self.assertContains(detail, "15 min")
        self.assertContains(detail, "30 min")

    def test_room_user_screen_hides_operational_tolerances_and_uses_planned_end(self):
        self.select_room_user()
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(9)),
            ends_at=self.aware(self.tomorrow, time(10)),
            created_by_profile="ROOM_USER",
        )

        agenda = self.client.get("/sala/agenda/")
        with patch(
            "apps.operations.availability.timezone.now",
            return_value=self.fixed_now,
        ):
            detail = self.client.get(
                f"/sala/computadores/{self.computer.pk}/?day=today",
                HTTP_HX_REQUEST="true",
            )

        self.assertContains(agenda, "09:00–10:00")
        self.assertNotContains(
            agenda, reservation.check_in_deadline_at.strftime("%H:%M")
        )
        self.assertNotContains(agenda, reservation.exit_deadline_at.strftime("%H:%M"))
        self.assertContains(detail, 'name="planned_ends_at"')
        self.assertNotContains(detail, 'name="slot_count"')

    def test_agenda_and_problems_paginate_without_losing_search(self):
        self.select_room_user()
        reservations = []
        for index in range(26):
            starts_at = self.fixed_now - timedelta(days=index + 1)
            reservations.append(
                create_reservation(
                    user_reference="aluno-si-001",
                    computer=self.computer,
                    starts_at=starts_at,
                    ends_at=starts_at + timedelta(minutes=15),
                    status=Reservation.Status.CANCELLED,
                    cancelled_by_profile="ROOM_USER",
                    cancelled_at=starts_at - timedelta(hours=1),
                    cancellation_reason=f"Cancelamento pesquisável {index}",
                    created_by_profile="ROOM_USER",
                )
            )
            Occurrence.objects.create(
                reported_by_reference="aluno-si-001",
                computer=self.computer,
                description=f"Problema paginado {index}",
            )

        agenda = self.client.get("/sala/agenda/?page=2")
        agenda_search = self.client.get("/sala/agenda/?q=pesquisável+0")
        problems = self.client.get("/sala/problemas/?page=2")

        self.assertContains(agenda, 'aria-label="Paginação"')
        self.assertContains(agenda, "Página 2 de 2")
        self.assertContains(agenda, reservations[-1].computer.description)
        self.assertContains(agenda_search, "Cancelamento pesquisável 0")
        self.assertNotContains(agenda_search, "Cancelamento pesquisável 1")
        self.assertContains(problems, 'aria-label="Paginação"')
        self.assertContains(problems, "Página 2 de 2")

    def test_computers_present_closed_room(self):
        self.select_room_user()
        OperatingSchedule.objects.all().delete()
        create_operating_schedule(
            valid_from=self.today - timedelta(days=1),
            weekday_windows={(self.today.weekday() + 1) % 7: [(time(7), time(22))]},
        )

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=self.fixed_now,
        ):
            response = self.client.get("/sala/computadores/?day=today")

        self.assertContains(response, "Sala fechada")
        self.assertContains(response, "Sem funcionamento nesta data")

    def test_creates_reservations_for_today_and_tomorrow(self):
        self.select_room_user()
        today_start = self.aware(self.today, time(9))
        tomorrow_start = self.aware(self.tomorrow, time(9))

        with patch(
            "apps.operations.services.reservations.timezone.now",
            return_value=self.fixed_now,
        ):
            today_response = self.client.post(
                "/sala/reservas/",
                {
                    "computer_id": self.computer.pk,
                    "day": "today",
                    "starts_at": today_start.isoformat(),
                    "slot_count": 2,
                },
            )
        tomorrow_response = self.client.post(
            "/sala/reservas/",
            {
                "computer_id": self.other_computer.pk,
                "day": "tomorrow",
                "starts_at": tomorrow_start.isoformat(),
                "slot_count": 3,
            },
        )

        self.assertRedirects(today_response, "/sala/agenda/")
        self.assertRedirects(tomorrow_response, "/sala/agenda/")
        self.assertEqual(Reservation.objects.count(), 2)
        self.assertEqual(
            Reservation.objects.get(computer=self.other_computer).ends_at,
            tomorrow_start + timedelta(minutes=45),
        )

    def test_booking_conflict_returns_refreshed_modal_without_persisting(self):
        self.select_room_user()
        starts_at = self.aware(self.tomorrow, time(9))
        create_reservation(
            user_reference="outro-usuario",
            computer=self.computer,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=30),
            created_by_profile="ROOM_USER",
        )

        response = self.client.post(
            "/sala/reservas/",
            {
                "computer_id": self.computer.pk,
                "day": "tomorrow",
                "starts_at": starts_at.isoformat(),
                "slot_count": 2,
            },
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="app-dialog-content",
        )

        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "conflita", status_code=409)
        self.assertContains(response, "Reservar horário", status_code=409)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_agenda_lists_and_cancels_owned_booking(self):
        self.select_room_user()
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(9)),
            ends_at=self.aware(self.tomorrow, time(10)),
            created_by_profile="ROOM_USER",
        )

        agenda = self.client.get("/sala/agenda/")
        cancel = self.client.post(f"/sala/reservas/{reservation.pk}/cancelar/")

        self.assertContains(agenda, "Confirmada")
        self.assertContains(agenda, "09:00–10:00")
        self.assertRedirects(cancel, "/sala/agenda/")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)

    def test_agenda_refreshes_entry_action_when_check_in_window_opens(self):
        self.select_room_user()
        create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.today, time(9)),
            ends_at=self.aware(self.today, time(10)),
            created_by_profile="ROOM_USER",
        )

        with patch(
            "apps.web.views.timezone.now",
            return_value=self.aware(self.today, time(8, 56, 59)),
        ):
            before_window = self.client.get("/sala/agenda/")

        self.assertNotContains(before_window, "Registrar entrada")
        self.assertContains(before_window, 'hx-trigger="every 15s"')
        self.assertContains(before_window, 'hx-target="#agenda-content"')

        with patch(
            "apps.web.views.timezone.now",
            return_value=self.aware(self.today, time(8, 57)),
        ):
            refreshed = self.client.get(
                "/sala/agenda/",
                HTTP_HX_REQUEST="true",
                HTTP_HX_TARGET="agenda-content",
            )

        self.assertContains(refreshed, 'id="agenda-content"', count=1)
        self.assertNotContains(refreshed, "<!doctype html>")
        self.assertNotContains(refreshed, "08:57")
        self.assertNotContains(refreshed, "09:03")
        self.assertContains(refreshed, "Registrar entrada")

    def test_immediate_session_switch_and_finish_flow(self):
        self.select_room_user()
        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.fixed_now,
        ):
            start = self.client.post(
                "/sala/sessao/iniciar/",
                {
                    "computer_id": self.computer.pk,
                    "planned_ends_at": self.aware(self.today, time(9)).isoformat(),
                    "user_reference": "identidade-injetada",
                    "affiliation_type": "PROFESSOR",
                    "institutional_unit": "Unidade injetada",
                },
            )
        active_session = UseSession.objects.get()

        with patch(
            "apps.operations.availability.timezone.now",
            return_value=self.fixed_now + timedelta(minutes=1),
        ):
            computers_page = self.client.get("/sala/computadores/?day=today")

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.fixed_now + timedelta(minutes=10),
        ):
            switch = self.client.post(
                f"/sala/sessao/{active_session.pk}/trocar/",
                {"computer_id": self.other_computer.pk},
            )
        session_page = self.client.get("/sala/sessao/")

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.fixed_now + timedelta(minutes=20),
        ):
            finish = self.client.post(f"/sala/sessao/{active_session.pk}/encerrar/")

        self.assertRedirects(start, "/sala/sessao/")
        self.assertEqual(active_session.user_reference, "aluno-si-001")
        self.assertEqual(active_session.affiliation_type, "STUDENT")
        self.assertEqual(
            active_session.institutional_unit,
            "Sistemas de Informação",
        )
        self.assertContains(computers_page, "Ocupado")
        self.assertRedirects(switch, "/sala/sessao/")
        self.assertContains(session_page, "PC-01")
        self.assertContains(session_page, "PC-02")
        self.assertRedirects(finish, "/sala/computadores/")
        active_session.refresh_from_db()
        self.assertEqual(active_session.status, UseSession.Status.FINISHED)
        self.assertEqual(active_session.allocations.count(), 2)

    def test_confirmation_forms_keep_their_non_javascript_post_fallback(self):
        self.select_room_user()
        reservation = create_reservation(
            user_reference="aluno-si-001",
            computer=self.computer,
            starts_at=self.aware(self.tomorrow, time(9)),
            ends_at=self.aware(self.tomorrow, time(10)),
            created_by_profile="ROOM_USER",
        )

        agenda = self.client.get("/sala/agenda/")
        response = self.client.post(f"/sala/reservas/{reservation.pk}/cancelar/")

        self.assertContains(agenda, "data-confirm-form")
        self.assertContains(agenda, "data-confirm-dialog")
        self.assertRedirects(response, "/sala/agenda/")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)

    def test_concurrent_immediate_start_refreshes_modal_with_error(self):
        self.select_room_user()
        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.fixed_now,
        ):
            self.client.post(
                "/sala/sessao/iniciar/",
                {
                    "computer_id": self.computer.pk,
                    "planned_ends_at": self.aware(self.today, time(9)).isoformat(),
                },
            )
        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.fixed_now + timedelta(minutes=1),
        ):
            response = self.client.post(
                "/sala/sessao/iniciar/",
                {
                    "computer_id": self.other_computer.pk,
                    "planned_ends_at": self.aware(self.today, time(8, 30)).isoformat(),
                },
                HTTP_HX_REQUEST="true",
                HTTP_HX_TARGET="app-dialog-content",
            )

        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "já possui uma sessão ativa", status_code=409)
        self.assertContains(response, "Trocar para este computador", status_code=409)
        self.assertEqual(UseSession.objects.count(), 1)

    def test_mutation_routes_reject_get(self):
        self.select_room_user()

        response = self.client.get("/sala/sessao/iniciar/")

        self.assertEqual(response.status_code, 405)

    def test_invalid_immediate_start_stays_in_accessible_modal(self):
        self.select_room_user()

        response = self.client.post(
            "/sala/sessao/iniciar/",
            {"computer_id": self.computer.pk, "planned_ends_at": ""},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="app-dialog-content",
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'role="alert"', status_code=400)
        self.assertEqual(UseSession.objects.count(), 0)

    def test_booking_check_in_starts_session(self):
        self.select_room_user()
        reservation = create_reservation(
            user_reference="aluno-si-001",
            affiliation_type="STUDENT",
            institutional_unit="Sistemas de Informação",
            computer=self.computer,
            starts_at=self.aware(self.today, time(9)),
            ends_at=self.aware(self.today, time(10)),
            created_by_profile="ROOM_USER",
        )

        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.aware(self.today, time(8, 57)),
        ):
            response = self.client.post(f"/sala/reservas/{reservation.pk}/entrada/")

        self.assertRedirects(response, "/sala/sessao/")
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.USED)
        session = UseSession.objects.get()
        self.assertEqual(session.reservation, reservation)
        self.assertEqual(session.started_at, self.aware(self.today, time(8, 57)))

    def test_problem_is_linked_to_matching_active_allocation(self):
        self.select_room_user()
        with patch(
            "apps.operations.services.usage_sessions.timezone.now",
            return_value=self.fixed_now,
        ):
            self.client.post(
                "/sala/sessao/iniciar/",
                {
                    "computer_id": self.computer.pk,
                    "planned_ends_at": self.aware(self.today, time(9)).isoformat(),
                },
            )
        active_session = UseSession.objects.get()
        allocation = active_session.allocations.get()

        response = self.client.post(
            "/sala/problemas/",
            {
                "computer_id": self.computer.pk,
                "description": "O mouse não está funcionando.",
            },
        )

        self.assertRedirects(response, "/sala/problemas/")
        occurrence = active_session.occurrences.get()
        self.assertEqual(occurrence.computer, self.computer)
        self.assertEqual(occurrence.allocation, allocation)

        Occurrence.objects.create(
            reported_by_reference="outro-usuario",
            computer=self.other_computer,
            description="Ocorrência de outra pessoa.",
        )
        own_problems = self.client.get("/sala/problemas/")
        self.assertContains(own_problems, "O mouse não está funcionando.")
        self.assertNotContains(own_problems, "Ocorrência de outra pessoa.")
