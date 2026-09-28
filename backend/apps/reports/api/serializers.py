from rest_framework import serializers

from apps.configuration.calendar import (
    CALENDAR_SOURCE_CHOICES,
    ROOM_STATUS_CHOICES,
)
from apps.configuration.models import ReportConfiguration


class DailyReportQuerySerializer(serializers.Serializer):
    date = serializers.DateField()


class MonthlyReportQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=1, max_value=9998)
    month = serializers.IntegerField(min_value=1, max_value=12)


class AnnualReportQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=1, max_value=9998)


class IndicatorsReportQuerySerializer(serializers.Serializer):
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()

    def validate(self, attrs):
        if attrs["ends_on"] < attrs["starts_on"]:
            raise serializers.ValidationError(
                {"ends_on": "A data final não pode ser anterior à inicial."}
            )
        if (attrs["ends_on"] - attrs["starts_on"]).days + 1 > 366:
            raise serializers.ValidationError(
                {"ends_on": "O período pode possuir no máximo 366 dias."}
            )
        return attrs


def _export_format_field():
    return serializers.ChoiceField(
        choices=ReportConfiguration.ExportFormat.choices,
        required=False,
    )


class DailyReportExportQuerySerializer(DailyReportQuerySerializer):
    format = _export_format_field()


class MonthlyReportExportQuerySerializer(MonthlyReportQuerySerializer):
    format = _export_format_field()


class AnnualReportExportQuerySerializer(AnnualReportQuerySerializer):
    format = _export_format_field()


class IndicatorsReportExportQuerySerializer(IndicatorsReportQuerySerializer):
    format = _export_format_field()


class ReportPeriodSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class DailyReportPeriodSerializer(serializers.Serializer):
    date = serializers.DateField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class AnnualReportPeriodSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class IndicatorsReportPeriodSerializer(serializers.Serializer):
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class ReportShiftSerializer(serializers.Serializer):
    series_key = serializers.UUIDField()
    name = serializers.CharField()
    display_order = serializers.IntegerField()


class MonthlyReportDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    day = serializers.IntegerField()
    calendar_status = serializers.ChoiceField(choices=ROOM_STATUS_CHOICES)
    calendar_source = serializers.ChoiceField(choices=CALENDAR_SOURCE_CHOICES)
    operating_minutes = serializers.IntegerField(min_value=0)
    visits_by_shift = serializers.DictField(child=serializers.IntegerField(min_value=0))
    total = serializers.IntegerField(min_value=0)


class MonthlyReportSummarySerializer(serializers.Serializer):
    visits = serializers.IntegerField(min_value=0)
    distinct_users = serializers.IntegerField(min_value=0)
    reservations = serializers.IntegerField(min_value=0)
    reservations_by_status = serializers.DictField(
        child=serializers.IntegerField(min_value=0)
    )
    occurrences = serializers.IntegerField(min_value=0)
    computers_used = serializers.IntegerField(min_value=0)
    allocated_minutes = serializers.IntegerField(min_value=0)
    average_stay_minutes = serializers.IntegerField(min_value=0)
    operating_minutes = serializers.IntegerField(min_value=0)


class ReportOccupancySerializer(serializers.Serializer):
    allocated_minutes = serializers.IntegerField(min_value=0)
    available_minutes = serializers.IntegerField(min_value=0)
    rate_percent = serializers.FloatField(allow_null=True)
    computers_considered = serializers.IntegerField(min_value=0)
    computers_excluded = serializers.IntegerField(min_value=0)
    calculated_until = serializers.DateTimeField()


class MonthlyReportWarningsSerializer(serializers.Serializer):
    active_session_ids = serializers.ListField(child=serializers.IntegerField())
    sessions_without_shift = serializers.ListField(child=serializers.IntegerField())
    computers_without_reliable_state_history = serializers.ListField(
        child=serializers.CharField()
    )


class MonthlyReportSerializer(serializers.Serializer):
    period = ReportPeriodSerializer()
    shifts = ReportShiftSerializer(many=True)
    days = MonthlyReportDaySerializer(many=True)
    totals_by_shift = serializers.DictField(child=serializers.IntegerField(min_value=0))
    summary = MonthlyReportSummarySerializer()
    occupancy = ReportOccupancySerializer()
    warnings = MonthlyReportWarningsSerializer()


class CalendarWindowSerializer(serializers.Serializer):
    opens_at = serializers.TimeField()
    closes_at = serializers.TimeField()


class DailyCalendarSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ROOM_STATUS_CHOICES)
    source = serializers.ChoiceField(choices=CALENDAR_SOURCE_CHOICES)
    reason = serializers.CharField(allow_blank=True)
    windows = CalendarWindowSerializer(many=True)
    operating_minutes = serializers.IntegerField(min_value=0)


class DailyReportSerializer(serializers.Serializer):
    period = DailyReportPeriodSerializer()
    calendar = DailyCalendarSerializer()
    shifts = ReportShiftSerializer(many=True)
    visits_by_shift = serializers.DictField(child=serializers.IntegerField(min_value=0))
    total = serializers.IntegerField(min_value=0)
    summary = MonthlyReportSummarySerializer()
    occupancy = ReportOccupancySerializer()
    warnings = MonthlyReportWarningsSerializer()


class AnnualReportMonthSerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    visits_by_shift = serializers.DictField(child=serializers.IntegerField(min_value=0))
    total = serializers.IntegerField(min_value=0)
    summary = MonthlyReportSummarySerializer()
    occupancy = ReportOccupancySerializer()


class AnnualReportSerializer(serializers.Serializer):
    period = AnnualReportPeriodSerializer()
    shifts = ReportShiftSerializer(many=True)
    months = AnnualReportMonthSerializer(many=True)
    totals_by_shift = serializers.DictField(child=serializers.IntegerField(min_value=0))
    summary = MonthlyReportSummarySerializer()
    occupancy = ReportOccupancySerializer()
    warnings = MonthlyReportWarningsSerializer()


class IndicatorMetricSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    visits = serializers.IntegerField(min_value=0)
    distinct_users = serializers.IntegerField(min_value=0, required=False)
    allocated_minutes = serializers.IntegerField(min_value=0)


class ComputerIndicatorSerializer(serializers.Serializer):
    computer_id = serializers.IntegerField()
    code = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    available_minutes = serializers.IntegerField(min_value=0)
    allocated_minutes = serializers.IntegerField(min_value=0)
    occupancy_rate_percent = serializers.FloatField(allow_null=True)
    visits = serializers.IntegerField(min_value=0)
    occurrences = serializers.IntegerField(min_value=0)


class DayIndicatorSerializer(serializers.Serializer):
    date = serializers.DateField()
    visits = serializers.IntegerField(min_value=0)
    allocated_minutes = serializers.IntegerField(min_value=0)
    available_minutes = serializers.IntegerField(min_value=0)
    occupancy_rate_percent = serializers.FloatField(allow_null=True)


class TimeSlotIndicatorSerializer(serializers.Serializer):
    starts_at = serializers.TimeField()
    allocated_minutes = serializers.IntegerField(min_value=0)
    available_minutes = serializers.IntegerField(min_value=0)
    occupancy_rate_percent = serializers.FloatField(allow_null=True)


class IndicatorsReportSerializer(serializers.Serializer):
    period = IndicatorsReportPeriodSerializer()
    summary = MonthlyReportSummarySerializer()
    occupancy = ReportOccupancySerializer()
    by_shift = IndicatorMetricSerializer(many=True)
    by_affiliation = IndicatorMetricSerializer(many=True)
    by_institutional_unit = IndicatorMetricSerializer(many=True)
    by_computer = ComputerIndicatorSerializer(many=True)
    by_day = DayIndicatorSerializer(many=True)
    by_time_slot = TimeSlotIndicatorSerializer(many=True)
    busiest_days = DayIndicatorSerializer(many=True)
    busiest_time_slots = TimeSlotIndicatorSerializer(many=True)
    reservations_by_status = serializers.DictField(
        child=serializers.IntegerField(min_value=0)
    )
    occurrences_by_status = serializers.DictField(
        child=serializers.IntegerField(min_value=0)
    )
    warnings = MonthlyReportWarningsSerializer()
