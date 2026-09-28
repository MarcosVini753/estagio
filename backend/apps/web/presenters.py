import unicodedata

from django.utils import timezone

from apps.computers.models import Computer
from apps.operations.rules import SLOT_DURATION_MINUTES

STATUS_META = {
    Computer.OperationalState.AVAILABLE: {
        "label": "Disponível",
        "tone": "success",
        "description": "Pronto para uso",
    },
    Computer.OperationalState.MAINTENANCE: {
        "label": "Manutenção",
        "tone": "danger",
        "description": "Indisponível para uso",
    },
    Computer.OperationalState.INACTIVE: {
        "label": "Inativo",
        "tone": "danger",
        "description": "Fora de operação",
    },
    "OCCUPIED": {
        "label": "Ocupado",
        "tone": "neutral",
        "description": "Em sessão de uso",
    },
    "RESERVED": {
        "label": "Reservado",
        "tone": "warning",
        "description": "Possui reserva neste horário",
    },
}


def normalize_search(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).lower()


def computer_rows(
    *, summary: dict, computers: list[Computer], query: str
) -> list[dict]:
    by_id = {computer.pk: computer for computer in computers}
    rows = []
    normalized_query = normalize_search(query)
    for item in summary["computers"]:
        computer = by_id[item["id"]]
        if summary["is_today"]:
            effective_status = item["effective_status_now"] or item["operational_state"]
            meta = STATUS_META[effective_status]
            availability_note = meta["description"]
        elif item["operational_state"] != Computer.OperationalState.AVAILABLE:
            effective_status = item["operational_state"]
            meta = STATUS_META[effective_status]
            availability_note = meta["description"]
        elif item["available_slot_count"]:
            effective_status = Computer.OperationalState.AVAILABLE
            meta = STATUS_META[effective_status]
            count = item["available_slot_count"]
            slot_label = "horário disponível" if count == 1 else "horários disponíveis"
            availability_note = f"{count} {slot_label}"
        else:
            effective_status = "NO_SLOTS"
            meta = {
                "label": "Sem horários",
                "tone": "neutral",
                "description": "Nenhum horário selecionável",
            }
            availability_note = meta["description"]

        searchable = normalize_search(
            " ".join(
                [
                    computer.code,
                    computer.description,
                    computer.notes,
                    meta["label"],
                    availability_note,
                ]
            )
        )
        if normalized_query and normalized_query not in searchable:
            continue
        code_label = computer.code.replace("-", "")
        rows.append(
            {
                **item,
                "computer": computer,
                "code_label": code_label,
                "status": effective_status,
                "status_label": meta["label"],
                "status_tone": meta["tone"],
                "availability_note": availability_note,
            }
        )
    return rows


def slot_rows(slots: list[dict], selected_starts_at: str = "") -> list[dict]:
    rows = []
    for slot in slots:
        starts_at = slot["starts_at"]
        value = starts_at.isoformat()
        meta = STATUS_META[slot["effective_status"]]
        rows.append(
            {
                **slot,
                "value": value,
                "time_label": timezone.localtime(starts_at).strftime("%H:%M"),
                "ends_label": timezone.localtime(slot["ends_at"]).strftime("%H:%M"),
                "selected": value == selected_starts_at,
                "status_label": meta["label"],
            }
        )
    return rows


def reservation_duration_options(
    slots: list[dict], selected_starts_at: str
) -> list[dict]:
    selected_index = next(
        (
            index
            for index, slot in enumerate(slots)
            if slot["starts_at"].isoformat() == selected_starts_at
        ),
        None,
    )
    if selected_index is None or not slots[selected_index]["selectable"]:
        return []

    selected = slots[selected_index]
    options = []
    previous_end = selected["starts_at"]
    for slot in slots[selected_index:]:
        if not slot["selectable"] or slot["starts_at"] != previous_end:
            break
        slot_count = len(options) + 1
        starts_at = selected["starts_at"]
        ends_at = slot["ends_at"]
        options.append(
            {
                "slot_count": slot_count,
                "minutes": slot_count * SLOT_DURATION_MINUTES,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "starts_label": timezone.localtime(starts_at).strftime("%H:%M"),
                "ends_label": timezone.localtime(ends_at).strftime("%H:%M"),
            }
        )
        previous_end = slot["ends_at"]
    return options


def immediate_end_options(
    immediate_usage: dict, *, selected_planned_ends_at: str = ""
) -> list[dict]:
    return [
        {
            "value": planned_ends_at.isoformat(),
            "planned_ends_label": timezone.localtime(planned_ends_at).strftime("%H:%M"),
            "selected": planned_ends_at.isoformat() == selected_planned_ends_at,
        }
        for planned_ends_at in immediate_usage.get("planned_end_options", [])
    ]


def flatten_serializer_errors(errors) -> str:
    messages = []
    for field, values in errors.items():
        if isinstance(values, dict):
            messages.append(flatten_serializer_errors(values))
            continue
        if not isinstance(values, (list, tuple)):
            values = [values]
        label = "" if field in {"non_field_errors", "detail"} else f"{field}: "
        messages.extend(f"{label}{value}" for value in values)
    return " ".join(message for message in messages if message)
