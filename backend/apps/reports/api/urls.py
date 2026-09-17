from django.urls import path

from .views import (
    AnnualReportAPIView,
    AnnualReportExportAPIView,
    DailyReportAPIView,
    DailyReportExportAPIView,
    IndicatorsReportAPIView,
    IndicatorsReportExportAPIView,
    MonthlyReportAPIView,
    MonthlyReportExportAPIView,
)

urlpatterns = [
    path("reports/daily/", DailyReportAPIView.as_view(), name="report-daily"),
    path(
        "reports/daily/export/",
        DailyReportExportAPIView.as_view(),
        name="report-daily-export",
    ),
    path("reports/monthly/", MonthlyReportAPIView.as_view(), name="report-monthly"),
    path(
        "reports/monthly/export/",
        MonthlyReportExportAPIView.as_view(),
        name="report-monthly-export",
    ),
    path("reports/annual/", AnnualReportAPIView.as_view(), name="report-annual"),
    path(
        "reports/annual/export/",
        AnnualReportExportAPIView.as_view(),
        name="report-annual-export",
    ),
    path(
        "reports/indicators/",
        IndicatorsReportAPIView.as_view(),
        name="report-indicators",
    ),
    path(
        "reports/indicators/export/",
        IndicatorsReportExportAPIView.as_view(),
        name="report-indicators-export",
    ),
]
