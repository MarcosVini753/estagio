from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.configuration.calendar import (
    CALENDAR_SOURCE_CHOICES,
    ROOM_STATUS_CHOICES,
)
from apps.configuration.models import (
    BookingPolicy,
    CalendarException,
    OperatingSchedule,
    OperatingScheduleDay,
    OperatingWindow,
    RoomNotice,
    Shift,
    Weekday,
)


class RoomNoticeInlineSerializer(serializers.Serializer):
    notice_type = serializers.ChoiceField(
        choices=RoomNotice.NoticeType.choices,
        required=False,
    )
    title = serializers.CharField(max_length=150)
    message = serializers.CharField()
    effective_from = serializers.DateField(required=False)
    effective_until = serializers.DateField(required=False)
    visible_from = serializers.DateTimeField()
    visible_until = serializers.DateTimeField(required=False, allow_null=True)


class WeekdayField(serializers.ChoiceField):
    def __init__(self, **kwargs):
        super().__init__(choices=Weekday.choices, **kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str) and data in Weekday.__members__:
            return Weekday[data].value
        return super().to_internal_value(data)

    def to_representation(self, value):
        if value in (None, ""):
            return value
        return Weekday(int(value)).name


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            "id",
            "series_key",
            "name",
            "start_time",
            "end_time",
            "display_order",
            "valid_from",
            "valid_until",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "series_key", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
        if instance and instance.use_sessions.exists() and attrs:
            if set(attrs) != {"is_active"} or attrs["is_active"] is not False:
                raise serializers.ValidationError(
                    "Turnos usados são imutáveis; apenas a desativação é permitida."
                )
        start_time = attrs.get(
            "start_time",
            instance.start_time if instance else None,
        )
        end_time = attrs.get("end_time", instance.end_time if instance else None)
        valid_from = attrs.get(
            "valid_from",
            instance.valid_from if instance else timezone.localdate(),
        )
        valid_until = attrs.get(
            "valid_until",
            instance.valid_until if instance else None,
        )
        is_active = attrs.get("is_active", instance.is_active if instance else True)

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError(
                {"end_time": "O horário final deve ser posterior ao horário inicial."}
            )
        if valid_until and valid_until < valid_from:
            raise serializers.ValidationError(
                {"valid_until": "A validade final não pode anteceder a inicial."}
            )

        if not is_active or not start_time or not end_time:
            return attrs

        conflicts = Shift.objects.filter(
            is_active=True,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=valid_from))
        if valid_until:
            conflicts = conflicts.filter(valid_from__lte=valid_until)
        if instance:
            conflicts = conflicts.exclude(pk=instance.pk)
        if conflicts.exists():
            raise serializers.ValidationError(
                {"non_field_errors": ["O turno sobrepõe outro turno ativo."]}
            )
        return attrs


class ShiftReplaceSerializer(serializers.Serializer):
    effective_from = serializers.DateField()
    name = serializers.CharField(max_length=100)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    display_order = serializers.IntegerField(min_value=0)

    def validate_effective_from(self, value):
        if value <= timezone.localdate():
            raise serializers.ValidationError("A vigência deve começar após hoje.")
        return value

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(
                {"end_time": "O horário final deve ser posterior ao horário inicial."}
            )
        return attrs


class CalendarExceptionSerializer(serializers.ModelSerializer):
    confirm_invalidation = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    notify_users = serializers.BooleanField(
        write_only=True,
        required=False,
        default=False,
    )
    notice = RoomNoticeInlineSerializer(write_only=True, required=False)

    class Meta:
        model = CalendarException
        fields = [
            "id",
            "date",
            "exception_type",
            "opens_at",
            "closes_at",
            "description",
            "confirm_invalidation",
            "notify_users",
            "notice",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
        if instance and "date" in attrs and attrs["date"] != instance.date:
            raise serializers.ValidationError(
                {"date": "A data da exceção não pode ser alterada."}
            )
        exception_type = attrs.get(
            "exception_type",
            instance.exception_type if instance else None,
        )
        opens_at = attrs.get("opens_at", instance.opens_at if instance else None)
        closes_at = attrs.get("closes_at", instance.closes_at if instance else None)

        if exception_type == CalendarException.ExceptionType.SPECIAL_HOURS:
            if not opens_at or not closes_at:
                raise serializers.ValidationError(
                    "Horário especial exige abertura e fechamento."
                )
            if opens_at >= closes_at:
                raise serializers.ValidationError(
                    "O horário de abertura deve anteceder o fechamento."
                )
        elif opens_at or closes_at:
            raise serializers.ValidationError(
                "Horários só devem ser informados para uma exceção de horário especial."
            )
        if attrs.get("notify_users") and not attrs.get("notice"):
            raise serializers.ValidationError(
                {"notice": "Informe o aviso quando notify_users for verdadeiro."}
            )
        return attrs


class BookingPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingPolicy
        fields = [
            "id",
            "cancellation_limit_minutes",
            "max_future_reservations_per_user",
            "is_active",
            "valid_from",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_active",
            "valid_from",
            "created_at",
            "updated_at",
        ]


class BookingPolicyUpdateSerializer(serializers.Serializer):
    cancellation_limit_minutes = serializers.IntegerField(min_value=0, required=False)
    max_future_reservations_per_user = serializers.IntegerField(
        min_value=1,
        required=False,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Informe ao menos um campo para atualização."
            )
        return attrs


class OperatingWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatingWindow
        fields = ["id", "opens_at", "closes_at", "display_order"]
        read_only_fields = ["id"]


class OperatingScheduleDaySerializer(serializers.ModelSerializer):
    weekday = WeekdayField()
    windows = OperatingWindowSerializer(many=True)

    class Meta:
        model = OperatingScheduleDay
        fields = ["id", "weekday", "is_open", "windows"]
        read_only_fields = ["id"]


class OperatingScheduleSerializer(serializers.ModelSerializer):
    days = OperatingScheduleDaySerializer(many=True, read_only=True)

    class Meta:
        model = OperatingSchedule
        fields = [
            "id",
            "series_key",
            "name",
            "schedule_type",
            "valid_from",
            "valid_until",
            "reason",
            "is_active",
            "created_by_profile",
            "days",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OperatingWindowWriteSerializer(serializers.Serializer):
    opens_at = serializers.TimeField()
    closes_at = serializers.TimeField()
    display_order = serializers.IntegerField(min_value=0, required=False)


class OperatingScheduleDayWriteSerializer(serializers.Serializer):
    weekday = WeekdayField()
    is_open = serializers.BooleanField()
    windows = OperatingWindowWriteSerializer(many=True)


class OperatingScheduleCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    schedule_type = serializers.ChoiceField(
        choices=OperatingSchedule.ScheduleType.choices
    )
    valid_from = serializers.DateField()
    valid_until = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    days = OperatingScheduleDayWriteSerializer(many=True)
    confirm_invalidation = serializers.BooleanField(required=False, default=False)
    notify_users = serializers.BooleanField(required=False, default=False)
    notice = RoomNoticeInlineSerializer(required=False)

    def validate(self, attrs):
        if attrs.get("notify_users") and not attrs.get("notice"):
            raise serializers.ValidationError(
                {"notice": "Informe o aviso quando notify_users for verdadeiro."}
            )
        return attrs


class OperatingScheduleUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False)
    valid_from = serializers.DateField(required=False)
    valid_until = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    days = OperatingScheduleDayWriteSerializer(many=True, required=False)
    confirm_invalidation = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not set(attrs) - {"confirm_invalidation"}:
            raise serializers.ValidationError(
                "Informe ao menos um campo para atualização."
            )
        return attrs


class OperatingScheduleReplaceSerializer(serializers.Serializer):
    effective_from = serializers.DateField()
    name = serializers.CharField(max_length=120, required=False)
    reason = serializers.CharField(required=False, allow_blank=True)
    days = OperatingScheduleDayWriteSerializer(many=True, required=False)
    confirm_invalidation = serializers.BooleanField(required=False, default=False)
    notify_users = serializers.BooleanField(required=False, default=False)
    notice = RoomNoticeInlineSerializer(required=False)

    def validate(self, attrs):
        if attrs.get("notify_users") and not attrs.get("notice"):
            raise serializers.ValidationError(
                {"notice": "Informe o aviso quando notify_users for verdadeiro."}
            )
        return attrs


class OperatingScheduleImpactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    schedule_type = serializers.ChoiceField(
        choices=OperatingSchedule.ScheduleType.choices
    )
    valid_from = serializers.DateField()
    valid_until = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    days = OperatingScheduleDayWriteSerializer(many=True)


class AffectedPeriodSerializer(serializers.Serializer):
    starts_on = serializers.DateField()
    ends_on = serializers.DateField(allow_null=True)


class ConflictingReservationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user_reference = serializers.CharField()
    computer_id = serializers.IntegerField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    reason = serializers.CharField()


class OperatingScheduleImpactResponseSerializer(serializers.Serializer):
    affected_period = AffectedPeriodSerializer()
    conflicting_reservations = ConflictingReservationSerializer(many=True)
    total = serializers.IntegerField(min_value=0)


class RoomNoticeSerializer(serializers.ModelSerializer):
    operating_schedule_id = serializers.IntegerField(read_only=True)
    calendar_exception_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = RoomNotice
        fields = [
            "id",
            "notice_type",
            "title",
            "message",
            "effective_from",
            "effective_until",
            "visible_from",
            "visible_until",
            "is_active",
            "created_by_profile",
            "operating_schedule_id",
            "calendar_exception_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RoomNoticeCreateSerializer(serializers.Serializer):
    notice_type = serializers.ChoiceField(choices=RoomNotice.NoticeType.choices)
    title = serializers.CharField(max_length=150)
    message = serializers.CharField()
    effective_from = serializers.DateField()
    effective_until = serializers.DateField()
    visible_from = serializers.DateTimeField()
    visible_until = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)


class RoomNoticeUpdateSerializer(serializers.Serializer):
    notice_type = serializers.ChoiceField(
        choices=RoomNotice.NoticeType.choices,
        required=False,
    )
    title = serializers.CharField(max_length=150, required=False)
    message = serializers.CharField(required=False)
    effective_from = serializers.DateField(required=False)
    effective_until = serializers.DateField(required=False)
    visible_from = serializers.DateTimeField(required=False)
    visible_until = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Informe ao menos um campo para atualização."
            )
        return attrs


class RoomStatusQuerySerializer(serializers.Serializer):
    date = serializers.DateField(required=False, default=timezone.localdate)


class RoomStatusWindowSerializer(serializers.Serializer):
    opens_at = serializers.TimeField()
    closes_at = serializers.TimeField()


class RoomStatusSerializer(serializers.Serializer):
    date = serializers.DateField()
    status = serializers.ChoiceField(choices=ROOM_STATUS_CHOICES)
    source = serializers.ChoiceField(choices=CALENDAR_SOURCE_CHOICES)
    is_open_now = serializers.BooleanField()
    reason = serializers.CharField(allow_blank=True)
    operating_windows = RoomStatusWindowSerializer(many=True)
    active_notices = RoomNoticeSerializer(many=True)
