from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import HasDemoProfile
from apps.configuration.models import ReportConfiguration
from apps.core.enums import DemoProfile
from apps.reports.exports import build_export_document, render_export
from apps.reports.reporting import generate_report

from .serializers import (
    AnnualReportExportQuerySerializer,
    AnnualReportQuerySerializer,
    AnnualReportSerializer,
    DailyReportExportQuerySerializer,
    DailyReportQuerySerializer,
    DailyReportSerializer,
    IndicatorsReportExportQuerySerializer,
    IndicatorsReportQuerySerializer,
    IndicatorsReportSerializer,
    MonthlyReportExportQuerySerializer,
    MonthlyReportQuerySerializer,
    MonthlyReportSerializer,
)

EXPORT_RESPONSES = {
    (200, "text/csv"): OpenApiTypes.BINARY,
    (
        200,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ): OpenApiTypes.BINARY,
    (200, "application/pdf"): OpenApiTypes.BINARY,
}


class ManagementReportAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = [
        DemoProfile.LIBRARY_SUPERVISOR,
        DemoProfile.SYSTEM_ADMIN,
    ]
    query_serializer_class = None
    report_kind = ""

    def get_report(self, request):
        query = self.query_serializer_class(data=request.query_params)
        query.is_valid(raise_exception=True)
        return (
            generate_report(
                self.report_kind,
                query.validated_data,
                now=timezone.now(),
            ),
            query.validated_data,
        )


class JSONReportAPIView(ManagementReportAPIView):
    def report_response(self, request):
        report, _ = self.get_report(request)
        return Response(report)


class ExportReportAPIView(ManagementReportAPIView):
    def export_response(self, request):
        report, filters = self.get_report(request)
        configuration = (
            ReportConfiguration.objects.filter(is_active=True).first()
            or ReportConfiguration()
        )
        selected_format = filters.get("format") or configuration.default_format
        document = build_export_document(
            self.report_kind,
            report,
            configuration,
        )
        content, content_type, extension = render_export(document, selected_format)
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = (
            f'attachment; filename="{document.filename_stem}.{extension}"'
        )
        return response


class DailyReportAPIView(JSONReportAPIView):
    query_serializer_class = DailyReportQuerySerializer
    report_kind = "daily"

    @extend_schema(
        parameters=[DailyReportQuerySerializer],
        responses={200: DailyReportSerializer},
        tags=["reports"],
    )
    def get(self, request):
        return self.report_response(request)


class MonthlyReportAPIView(JSONReportAPIView):
    query_serializer_class = MonthlyReportQuerySerializer
    report_kind = "monthly"

    @extend_schema(
        parameters=[MonthlyReportQuerySerializer],
        responses={200: MonthlyReportSerializer},
        tags=["reports"],
    )
    def get(self, request):
        return self.report_response(request)


class AnnualReportAPIView(JSONReportAPIView):
    query_serializer_class = AnnualReportQuerySerializer
    report_kind = "annual"

    @extend_schema(
        parameters=[AnnualReportQuerySerializer],
        responses={200: AnnualReportSerializer},
        tags=["reports"],
    )
    def get(self, request):
        return self.report_response(request)


class IndicatorsReportAPIView(JSONReportAPIView):
    query_serializer_class = IndicatorsReportQuerySerializer
    report_kind = "indicators"

    @extend_schema(
        parameters=[IndicatorsReportQuerySerializer],
        responses={200: IndicatorsReportSerializer},
        tags=["reports"],
    )
    def get(self, request):
        return self.report_response(request)


class DailyReportExportAPIView(ExportReportAPIView):
    query_serializer_class = DailyReportExportQuerySerializer
    report_kind = "daily"

    @extend_schema(
        parameters=[DailyReportExportQuerySerializer],
        responses=EXPORT_RESPONSES,
        tags=["reports"],
    )
    def get(self, request):
        return self.export_response(request)


class MonthlyReportExportAPIView(ExportReportAPIView):
    query_serializer_class = MonthlyReportExportQuerySerializer
    report_kind = "monthly"

    @extend_schema(
        parameters=[MonthlyReportExportQuerySerializer],
        responses=EXPORT_RESPONSES,
        tags=["reports"],
    )
    def get(self, request):
        return self.export_response(request)


class AnnualReportExportAPIView(ExportReportAPIView):
    query_serializer_class = AnnualReportExportQuerySerializer
    report_kind = "annual"

    @extend_schema(
        parameters=[AnnualReportExportQuerySerializer],
        responses=EXPORT_RESPONSES,
        tags=["reports"],
    )
    def get(self, request):
        return self.export_response(request)


class IndicatorsReportExportAPIView(ExportReportAPIView):
    query_serializer_class = IndicatorsReportExportQuerySerializer
    report_kind = "indicators"

    @extend_schema(
        parameters=[IndicatorsReportExportQuerySerializer],
        responses=EXPORT_RESPONSES,
        tags=["reports"],
    )
    def get(self, request):
        return self.export_response(request)
