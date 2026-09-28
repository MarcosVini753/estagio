from django.utils import timezone

from apps.operations.services.deadlines import ReconcileScope, reconcile_deadlines

from .projections import (
    build_annual_report,
    build_daily_report,
    build_indicators_report,
    build_monthly_report,
    date_bounds,
    inclusive_period_bounds,
    month_bounds,
    year_bounds,
)
from .selectors import load_report_data


def _load(starts_at, ends_at, *, now):
    reconcile_deadlines(
        now=now,
        scope=ReconcileScope(period=(starts_at, ends_at)),
    )
    return load_report_data(
        starts_at=starts_at,
        ends_at=ends_at,
        starts_on=timezone.localdate(starts_at),
        ends_on=timezone.localdate(ends_at),
    )


def generate_daily_report(target_date, *, now=None):
    now = now or timezone.now()
    starts_at, ends_at = date_bounds(target_date)
    data = _load(starts_at, ends_at, now=now)
    return build_daily_report(
        target_date=target_date,
        **data.__dict__,
        now=now,
    )


def generate_monthly_report(year, month, *, now=None):
    now = now or timezone.now()
    starts_at, ends_at = month_bounds(year, month)
    data = _load(starts_at, ends_at, now=now)
    return build_monthly_report(
        year=year,
        month=month,
        **data.__dict__,
        now=now,
    )


def generate_annual_report(year, *, now=None):
    now = now or timezone.now()
    starts_at, ends_at = year_bounds(year)
    data = _load(starts_at, ends_at, now=now)
    return build_annual_report(
        year=year,
        **data.__dict__,
        now=now,
    )


def generate_indicators_report(starts_on, ends_on, *, now=None):
    now = now or timezone.now()
    starts_at, ends_at = inclusive_period_bounds(starts_on, ends_on)
    data = _load(starts_at, ends_at, now=now)
    return build_indicators_report(
        starts_on=starts_on,
        ends_on=ends_on,
        **data.__dict__,
        now=now,
    )


def generate_report(kind, filters, *, now=None):
    """Gera qualquer visão a partir de filtros já validados."""

    now = now or timezone.now()
    if kind == "daily":
        return generate_daily_report(filters["date"], now=now)
    if kind == "monthly":
        return generate_monthly_report(
            filters["year"],
            filters["month"],
            now=now,
        )
    if kind == "annual":
        return generate_annual_report(filters["year"], now=now)
    if kind == "indicators":
        return generate_indicators_report(
            filters["starts_on"],
            filters["ends_on"],
            now=now,
        )
    raise ValueError(f"Tipo de relatório desconhecido: {kind}")


__all__ = [
    "generate_annual_report",
    "generate_daily_report",
    "generate_indicators_report",
    "generate_monthly_report",
    "generate_report",
]
