import random
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.computers.models import Computer, ComputerOperationalStateChange
from apps.configuration.calendar import as_datetime_windows, resolve_operating_day
from apps.configuration.models import (
    BookingPolicy,
    CalendarException,
    OperatingSchedule,
    ReportConfiguration,
    Shift,
)
from apps.core.enums import AffiliationType, DemoProfile
from apps.occurrences.models import Occurrence
from apps.operations.models import ComputerAllocation, Reservation, UseSession

from .seed_demo_data import ensure_regular_operating_schedule

DEMO_PREFIX = "demo-report-"
BASE_VALID_FROM = date(2025, 1, 1)
SHIFTS = [
    ("1º Turno", time(7, 15), time(13, 0), 1, time(8, 0)),
    ("2º Turno", time(13, 0), time(17, 0), 2, time(14, 0)),
    ("3º Turno", time(17, 0), time(21, 0), 3, time(18, 0)),
]
IDENTITIES = [
    (AffiliationType.STUDENT, "Sistemas de Informação"),
    (AffiliationType.STUDENT, "Direito"),
    (AffiliationType.STUDENT, "Engenharia Florestal"),
    (AffiliationType.PROFESSOR, "Centro de Ciências Exatas"),
    (AffiliationType.PROFESSOR, "Centro de Educação e Letras"),
    (AffiliationType.TECHNICAL_STAFF, "Biblioteca Central"),
    (AffiliationType.TECHNICAL_STAFF, "Pró-Reitoria de Graduação"),
]


def aware(target_date, target_time):
    return timezone.make_aware(
        datetime.combine(target_date, target_time),
        timezone.get_current_timezone(),
    )


class Command(BaseCommand):
    help = "Cria dados históricos fictícios, determinísticos e removíveis."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=60)
        parser.add_argument("--seed", type=int, default=12345)
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        days = options["days"]
        seed = options["seed"]
        if days < 3:
            raise CommandError("--days deve ser no mínimo 3.")
        if options["reset"]:
            self._reset_generated_data()
        seed_prefix = f"{DEMO_PREFIX}{seed}-"
        if (
            UseSession.objects.filter(user_reference__startswith=DEMO_PREFIX)
            .exclude(user_reference__startswith=seed_prefix)
            .exists()
        ):
            raise CommandError(
                "Já existem dados de outra semente. Execute novamente com --reset."
            )

        computers, shifts = self._ensure_canonical_data()
        dates = [
            timezone.localdate() - timedelta(days=days - offset)
            for offset in range(days)
        ]
        closed_date = dates[len(dates) // 3]
        special_date = dates[(2 * len(dates)) // 3]
        self._create_calendar(closed_date, special_date)

        sessions_by_date = {}
        for target_date in dates:
            operating_day = resolve_operating_day(target_date)
            if operating_day.is_closed:
                sessions_by_date[target_date] = []
                continue
            sessions_by_date[target_date] = self._create_day_sessions(
                target_date=target_date,
                seed=seed,
                rng=random.Random(f"{seed}:{target_date.isoformat()}"),
                computers=computers,
                shifts=shifts,
                operating_day=operating_day,
            )
            self._create_reservation(
                target_date=target_date,
                seed=seed,
                rng=random.Random(f"{seed}:reservation:{target_date.isoformat()}"),
                computers=computers,
                sessions=sessions_by_date[target_date],
            )
            if target_date.toordinal() % 4 == 0:
                self._create_occurrence(
                    target_date=target_date,
                    sessions=sessions_by_date[target_date],
                )

        self._create_maintenance_history(
            computer=computers[0],
            starts_at=aware(dates[len(dates) // 2], time(10, 0)),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Dados de relatório disponíveis de {dates[0]} a {dates[-1]} "
                f"({days} dias, semente {seed})."
            )
        )

    def _reset_generated_data(self):
        Occurrence.objects.filter(
            Q(reported_by_reference__startswith=DEMO_PREFIX)
            | Q(description__startswith=DEMO_PREFIX)
        ).delete()
        UseSession.objects.filter(user_reference__startswith=DEMO_PREFIX).delete()
        Reservation.objects.filter(user_reference__startswith=DEMO_PREFIX).delete()
        ComputerOperationalStateChange.objects.filter(
            reason__startswith=DEMO_PREFIX
        ).delete()
        CalendarException.objects.filter(description__startswith=DEMO_PREFIX).delete()

    def _ensure_canonical_data(self):
        if not OperatingSchedule.objects.filter(
            schedule_type=OperatingSchedule.ScheduleType.REGULAR,
            is_active=True,
        ).exists():
            ensure_regular_operating_schedule()
        computers = []
        for number in range(1, 9):
            computer, _ = Computer.objects.get_or_create(
                code=f"PC-{number:02d}",
                defaults={
                    "description": "Computador da Sala de Informática",
                    "notes": f"{DEMO_PREFIX}canônico",
                },
            )
            computers.append(computer)

        shifts = []
        for name, start_time, end_time, order, _ in SHIFTS:
            shift = Shift.objects.filter(
                name=name,
                display_order=order,
            ).first()
            if shift is None:
                shift = Shift.objects.create(
                    name=name,
                    start_time=start_time,
                    end_time=end_time,
                    display_order=order,
                    valid_from=BASE_VALID_FROM,
                )
            shifts.append(shift)

        if not BookingPolicy.objects.filter(is_active=True).exists():
            BookingPolicy.objects.create(
                slot_duration_minutes=60,
                check_in_tolerance_minutes=15,
                max_future_reservations_per_user=1,
                valid_from=BASE_VALID_FROM,
            )
        if not ReportConfiguration.objects.filter(is_active=True).exists():
            ReportConfiguration.objects.create()
        return computers, shifts

    def _create_calendar(self, closed_date, special_date):
        CalendarException.objects.get_or_create(
            date=closed_date,
            defaults={
                "exception_type": CalendarException.ExceptionType.CLOSED,
                "description": f"{DEMO_PREFIX}dia fechado",
            },
        )
        CalendarException.objects.get_or_create(
            date=special_date,
            defaults={
                "exception_type": CalendarException.ExceptionType.SPECIAL_HOURS,
                "opens_at": time(8, 0),
                "closes_at": time(20, 0),
                "description": f"{DEMO_PREFIX}horário especial",
            },
        )

    def _create_day_sessions(
        self,
        *,
        target_date,
        seed,
        rng,
        computers,
        shifts,
        operating_day,
    ):
        sessions = []
        operating_windows = as_datetime_windows(operating_day)
        for shift_index, (_, _, _, _, entry_time) in enumerate(SHIFTS):
            identity_index = (
                target_date.toordinal() * len(SHIFTS) + shift_index
            ) % len(IDENTITIES)
            affiliation, unit = IDENTITIES[identity_index]
            reference = f"{DEMO_PREFIX}{seed}-user-{identity_index:02d}"
            started_at = aware(target_date, entry_time)
            window_end = next(
                (
                    ends_at
                    for starts_at, ends_at in operating_windows
                    if starts_at <= started_at < ends_at
                ),
                None,
            )
            if window_end is None:
                continue
            duration = rng.choice([60, 90, 120, 150])
            ended_at = min(started_at + timedelta(minutes=duration), window_end)
            session, _ = UseSession.objects.get_or_create(
                user_reference=reference,
                started_at=started_at,
                defaults={
                    "affiliation_type": affiliation,
                    "institutional_unit": unit,
                    "ended_at": ended_at,
                    "status": UseSession.Status.FINISHED,
                    "start_shift": shifts[shift_index],
                    "entry_recorded_by_profile": DemoProfile.ROOM_USER,
                    "exit_recorded_by_profile": DemoProfile.ROOM_USER,
                },
            )
            if not session.allocations.exists():
                first_computer_index = (
                    target_date.toordinal() * len(SHIFTS) + shift_index
                ) % len(computers)
                if (target_date.toordinal() + shift_index) % 5 == 0:
                    switched_at = started_at + (ended_at - started_at) / 2
                    ComputerAllocation.objects.create(
                        session=session,
                        computer=computers[first_computer_index],
                        sequence=1,
                        started_at=started_at,
                        ended_at=switched_at,
                        end_reason=ComputerAllocation.EndReason.SWITCH,
                        switch_reason=f"{DEMO_PREFIX}troca planejada",
                    )
                    ComputerAllocation.objects.create(
                        session=session,
                        computer=computers[(first_computer_index + 1) % len(computers)],
                        sequence=2,
                        started_at=switched_at,
                        ended_at=ended_at,
                        end_reason=ComputerAllocation.EndReason.SESSION_FINISHED,
                    )
                else:
                    ComputerAllocation.objects.create(
                        session=session,
                        computer=computers[first_computer_index],
                        sequence=1,
                        started_at=started_at,
                        ended_at=ended_at,
                        end_reason=ComputerAllocation.EndReason.SESSION_FINISHED,
                    )
            sessions.append(session)
        return sessions

    def _create_reservation(
        self,
        *,
        target_date,
        seed,
        rng,
        computers,
        sessions,
    ):
        statuses = [
            Reservation.Status.CONFIRMED,
            Reservation.Status.USED,
            Reservation.Status.CANCELLED,
            Reservation.Status.NO_SHOW,
            Reservation.Status.INVALIDATED,
        ]
        reservation_status = statuses[target_date.toordinal() % len(statuses)]
        if reservation_status == Reservation.Status.USED and sessions:
            session = sessions[0]
            started_at = session.started_at
            computer = session.allocations.order_by("sequence").first().computer
            reference = session.user_reference
            affiliation = session.affiliation_type
            unit = session.institutional_unit
        else:
            identity_index = (target_date.toordinal() + 3) % len(IDENTITIES)
            affiliation, unit = IDENTITIES[identity_index]
            reference = f"{DEMO_PREFIX}{seed}-user-{identity_index:02d}"
            started_at = aware(target_date, time(11, 0))
            computer = computers[rng.randrange(len(computers))]
            session = None

        defaults = {
            "affiliation_type": affiliation,
            "institutional_unit": unit,
            "ends_at": started_at + timedelta(hours=1),
            "status": reservation_status,
            "created_by_profile": DemoProfile.ROOM_USER,
        }
        if reservation_status == Reservation.Status.CANCELLED:
            defaults.update(
                cancelled_by_profile=DemoProfile.ROOM_USER,
                cancelled_at=started_at - timedelta(hours=2),
                cancellation_reason=f"{DEMO_PREFIX}cancelamento fictício",
            )
        reservation, _ = Reservation.objects.get_or_create(
            user_reference=reference,
            computer=computer,
            starts_at=started_at,
            defaults=defaults,
        )
        if session is not None and session.reservation_id is None:
            session.reservation = reservation
            session.save(update_fields=["reservation", "updated_at"])

    def _create_occurrence(self, *, target_date, sessions):
        if not sessions:
            return
        session = sessions[target_date.toordinal() % len(sessions)]
        allocation = session.allocations.order_by("sequence").first()
        description = f"{DEMO_PREFIX}ocorrência-{target_date.isoformat()}"
        resolved = target_date.toordinal() % 8 == 0
        occurrence, created = Occurrence.objects.get_or_create(
            reported_by_reference=session.user_reference,
            description=description,
            defaults={
                "computer": allocation.computer,
                "session": session,
                "allocation": allocation,
                "status": (
                    Occurrence.Status.RESOLVED if resolved else Occurrence.Status.OPEN
                ),
                "resolved_by_profile": DemoProfile.INTERN if resolved else "",
                "resolution_notes": (
                    f"{DEMO_PREFIX}resolução fictícia" if resolved else ""
                ),
                "resolved_at": (
                    session.started_at + timedelta(hours=2) if resolved else None
                ),
            },
        )
        if created:
            Occurrence.objects.filter(pk=occurrence.pk).update(
                created_at=session.started_at + timedelta(minutes=15),
                updated_at=session.started_at + timedelta(minutes=15),
            )

    def _create_maintenance_history(self, *, computer, starts_at):
        changes = [
            (
                Computer.OperationalState.AVAILABLE,
                Computer.OperationalState.MAINTENANCE,
                starts_at,
            ),
            (
                Computer.OperationalState.MAINTENANCE,
                Computer.OperationalState.AVAILABLE,
                starts_at + timedelta(days=2),
            ),
        ]
        for previous_state, new_state, changed_at in changes:
            reason = (
                f"{DEMO_PREFIX}manutenção-{new_state.lower()}-"
                f"{changed_at.date().isoformat()}"
            )
            change, created = ComputerOperationalStateChange.objects.get_or_create(
                computer=computer,
                previous_state=previous_state,
                new_state=new_state,
                reason=reason,
                defaults={"actor_profile": DemoProfile.INTERN},
            )
            if created:
                ComputerOperationalStateChange.objects.filter(pk=change.pk).update(
                    changed_at=changed_at
                )
