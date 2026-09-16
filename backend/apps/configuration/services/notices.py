from django.db import transaction

from apps.audit.models import AuditEvent
from apps.core.api.errors import RoomNoticeInvalidPeriod, RoomNoticeMessageRequired

from ..models import CalendarException, OperatingSchedule, RoomNotice


def _validate_notice_values(values: dict) -> None:
    if not str(values.get("message", "")).strip():
        raise RoomNoticeMessageRequired()
    if values["effective_until"] < values["effective_from"]:
        raise RoomNoticeInvalidPeriod()
    if values.get("visible_until") and values["visible_until"] < values["visible_from"]:
        raise RoomNoticeInvalidPeriod()


@transaction.atomic
def create_room_notice(
    *,
    values: dict,
    actor_profile: str,
    operating_schedule: OperatingSchedule | None = None,
    calendar_exception: CalendarException | None = None,
) -> RoomNotice:
    _validate_notice_values(values)
    room_notice = RoomNotice.objects.create(
        **values,
        created_by_profile=actor_profile,
        operating_schedule=operating_schedule,
        calendar_exception=calendar_exception,
    )
    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="ROOM_NOTICE_CREATED",
        entity_type="RoomNotice",
        entity_id=str(room_notice.pk),
        new_values={
            "title": room_notice.title,
            "notice_type": room_notice.notice_type,
            "effective_from": room_notice.effective_from.isoformat(),
            "effective_until": room_notice.effective_until.isoformat(),
            "is_active": room_notice.is_active,
        },
    )
    return room_notice


@transaction.atomic
def update_room_notice(
    *,
    notice_id: int,
    values: dict,
    actor_profile: str,
) -> RoomNotice:
    notice = RoomNotice.objects.select_for_update().get(pk=notice_id)
    old_values = {
        field: getattr(notice, field)
        for field in [
            "notice_type",
            "title",
            "message",
            "effective_from",
            "effective_until",
            "visible_from",
            "visible_until",
            "is_active",
        ]
    }
    merged = {**old_values, **values}
    _validate_notice_values(merged)
    for field, value in values.items():
        setattr(notice, field, value)
    notice.save(update_fields=[*values.keys(), "updated_at"])

    def serialize(value):
        return value.isoformat() if hasattr(value, "isoformat") else value

    AuditEvent.objects.create(
        actor_profile=actor_profile,
        action="ROOM_NOTICE_UPDATED",
        entity_type="RoomNotice",
        entity_id=str(notice.pk),
        old_values={key: serialize(value) for key, value in old_values.items()},
        new_values={key: serialize(value) for key, value in merged.items()},
    )
    return notice

def notice_values_for_change(
    *,
    notice: dict,
    valid_from,
    valid_until,
    notice_type: str,
) -> dict:
    values = dict(notice)
    values.setdefault("notice_type", notice_type)
    values.setdefault("effective_from", valid_from)
    values.setdefault("effective_until", valid_until or valid_from)
    return values


def deactivate_schedule_notices(
    *,
    schedule: OperatingSchedule,
    actor_profile: str,
) -> None:
    notice_ids = list(
        schedule.notices.filter(is_active=True).values_list("pk", flat=True)
    )
    for notice_id in notice_ids:
        update_room_notice(
            notice_id=notice_id,
            values={"is_active": False},
            actor_profile=actor_profile,
        )


__all__ = [
    "create_room_notice",
    "deactivate_schedule_notices",
    "notice_values_for_change",
    "update_room_notice",
]
