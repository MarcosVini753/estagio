import hashlib
import json

SCHEDULE_PREVIEW_SESSION_KEY = "supervisor_schedule_preview"
EXCEPTION_PREVIEW_SESSION_KEY = "supervisor_exception_preview"


def fingerprint(kind, values):
    serialized = json.dumps(
        {"kind": kind, "values": values},
        sort_keys=True,
        default=str,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def remember_preview(
    request,
    *,
    key,
    values,
    impact,
    session_key=SCHEDULE_PREVIEW_SESSION_KEY,
):
    request.session[session_key] = {
        "key": key,
        "fingerprint": fingerprint(key, values),
        "total": impact["total"],
        "reservation_ids": [
            reservation["id"] for reservation in impact["conflicting_reservations"]
        ],
    }


def matching_preview(
    request,
    *,
    key,
    values,
    session_key=SCHEDULE_PREVIEW_SESSION_KEY,
):
    preview = request.session.get(session_key, {})
    return (
        preview
        if (
            preview.get("key") == key
            and preview.get("fingerprint") == fingerprint(key, values)
            and isinstance(preview.get("reservation_ids"), list)
        )
        else None
    )


__all__ = [
    "EXCEPTION_PREVIEW_SESSION_KEY",
    "SCHEDULE_PREVIEW_SESSION_KEY",
    "fingerprint",
    "matching_preview",
    "remember_preview",
]
