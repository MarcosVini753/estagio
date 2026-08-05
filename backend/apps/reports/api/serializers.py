from rest_framework import serializers


class MonthlyReportQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=1, max_value=9998)
    month = serializers.IntegerField(min_value=1, max_value=12)


class ReportPeriodSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class ReportShiftSerializer(serializers.Serializer):
    series_key = serializers.UUIDField()
    name = serializers.CharField()
    display_order = serializers.IntegerField()


class MonthlyReportDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    day = serializers.IntegerField()
    calendar_status = serializers.ChoiceField(
        choices=["OPEN", "CLOSED", "OPTIONAL_HOLIDAY", "SPECIAL_HOURS"]
    )
    visits_by_shift = serializers.DictField(child=serializers.IntegerField(min_value=0))
    total = serializers.IntegerField(min_value=0)


class MonthlyReportSummarySerializer(serializers.Serializer):
    visits = serializers.IntegerField(min_value=0)
    distinct_users = serializers.IntegerField(min_value=0)
    reservations = serializers.IntegerField(min_value=0)
    occurrences = serializers.IntegerField(min_value=0)
    computers_used = serializers.IntegerField(min_value=0)
    allocated_minutes = serializers.IntegerField(min_value=0)
    average_stay_minutes = serializers.IntegerField(min_value=0)


class MonthlyReportWarningsSerializer(serializers.Serializer):
    active_session_ids = serializers.ListField(child=serializers.IntegerField())
    sessions_without_shift = serializers.ListField(child=serializers.IntegerField())


class MonthlyReportSerializer(serializers.Serializer):
    period = ReportPeriodSerializer()
    shifts = ReportShiftSerializer(many=True)
    days = MonthlyReportDaySerializer(many=True)
    totals_by_shift = serializers.DictField(child=serializers.IntegerField(min_value=0))
    summary = MonthlyReportSummarySerializer()
    warnings = MonthlyReportWarningsSerializer()
