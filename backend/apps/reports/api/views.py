from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import HasDemoProfile
from apps.core.enums import DemoProfile
from apps.reports.projections import build_monthly_report, month_bounds
from apps.reports.selectors import (
    get_allocations_for_period,
    get_calendar_exceptions_for_period,
    get_occurrences_for_period,
    get_reservations_for_period,
    get_sessions_for_period,
    get_shifts_for_period,
)

from .serializers import MonthlyReportQuerySerializer, MonthlyReportSerializer


class MonthlyReportAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = [
        DemoProfile.LIBRARY_SUPERVISOR,
        DemoProfile.SYSTEM_ADMIN,
    ]

    @extend_schema(
        parameters=[MonthlyReportQuerySerializer],
        responses={200: MonthlyReportSerializer},
        tags=["reports"],
    )
    def get(self, request):
        query = MonthlyReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        year = query.validated_data["year"]
        month = query.validated_data["month"]
        starts_at, ends_at = month_bounds(year, month)

        report = build_monthly_report(
            year=year,
            month=month,
            sessions=get_sessions_for_period(starts_at, ends_at),
            allocations=get_allocations_for_period(starts_at, ends_at),
            reservations=get_reservations_for_period(starts_at, ends_at),
            occurrences=get_occurrences_for_period(starts_at, ends_at),
            shifts=get_shifts_for_period(starts_at.date(), ends_at.date()),
            calendar_exceptions=get_calendar_exceptions_for_period(
                starts_at.date(), ends_at.date()
            ),
        )
        return Response(report)
