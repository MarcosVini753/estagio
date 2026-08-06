from datetime import timedelta

from django.db import migrations
from django.db.models import Q

TOLERANCE = timedelta(minutes=3)


def backfill_model_c_deadlines(apps, schema_editor):
    Reservation = apps.get_model("operations", "Reservation")
    UseSession = apps.get_model("operations", "UseSession")

    legacy_active_sessions = UseSession.objects.filter(
        Q(status="ACTIVE") | Q(ended_at__isnull=True)
    )
    if legacy_active_sessions.exists():
        raise RuntimeError(
            "Finalize as sessões legadas ativas antes de aplicar o Modelo C."
        )

    for reservation in Reservation.objects.all().iterator(chunk_size=500):
        reservation.check_in_deadline_at = reservation.starts_at + TOLERANCE
        reservation.exit_deadline_at = reservation.ends_at + TOLERANCE
        if reservation.status == "NO_SHOW" and reservation.no_show_at is None:
            reservation.no_show_at = reservation.check_in_deadline_at
        reservation.save(
            update_fields=[
                "check_in_deadline_at",
                "exit_deadline_at",
                "no_show_at",
            ]
        )

    sessions = UseSession.objects.select_related("reservation")
    for session in sessions.iterator(chunk_size=500):
        if session.reservation_id:
            planned_starts_at = session.reservation.starts_at
            planned_ends_at = session.reservation.ends_at
            exit_deadline_at = session.reservation.exit_deadline_at
            if session.started_at < planned_starts_at:
                planned_starts_at = session.started_at
        else:
            planned_starts_at = session.started_at
            planned_ends_at = session.ended_at
            if planned_ends_at == planned_starts_at:
                planned_ends_at += timedelta.resolution
            exit_deadline_at = session.ended_at + TOLERANCE
        session.planned_starts_at = planned_starts_at
        session.planned_ends_at = planned_ends_at
        session.exit_deadline_at = exit_deadline_at
        session.save(
            update_fields=[
                "planned_starts_at",
                "planned_ends_at",
                "exit_deadline_at",
            ]
        )


def clear_model_c_deadlines(apps, schema_editor):
    Reservation = apps.get_model("operations", "Reservation")
    UseSession = apps.get_model("operations", "UseSession")
    Reservation.objects.update(
        check_in_deadline_at=None,
        exit_deadline_at=None,
        no_show_at=None,
    )
    UseSession.objects.update(
        planned_starts_at=None,
        planned_ends_at=None,
        exit_deadline_at=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0006_add_model_c_deadline_fields"),
    ]

    operations = [
        migrations.RunPython(
            backfill_model_c_deadlines,
            clear_model_c_deadlines,
        ),
    ]
