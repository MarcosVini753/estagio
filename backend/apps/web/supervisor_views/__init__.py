from .calendars import create_schedule, exceptions, replace_schedule
from .configuration import (
    configuration,
    configurations,
    notices,
    replace_shift_view,
    shifts,
    update_notice_state,
    update_shift,
)
from .dashboard import dashboard, reports
from .inventory import computers, update_computer

__all__ = [
    "computers",
    "configuration",
    "configurations",
    "create_schedule",
    "dashboard",
    "exceptions",
    "notices",
    "replace_schedule",
    "replace_shift_view",
    "reports",
    "shifts",
    "update_computer",
    "update_notice_state",
    "update_shift",
]
