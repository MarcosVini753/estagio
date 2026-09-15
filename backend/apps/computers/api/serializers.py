from rest_framework import serializers

from apps.computers.models import Computer
from apps.configuration.api.serializers import (
    RoomNoticeSerializer,
    RoomStatusWindowSerializer,
)
from apps.configuration.calendar import CALENDAR_SOURCE_CHOICES, ROOM_STATUS_CHOICES
from apps.operations.slotting import IMMEDIATE_USAGE_LIMIT_CHOICES

EFFECTIVE_STATUS_CHOICES = [
    Computer.OperationalState.AVAILABLE,
    Computer.OperationalState.MAINTENANCE,
    Computer.OperationalState.INACTIVE,
    "OCCUPIED",
    "RESERVED",
]


class ComputerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Computer
        fields = [
            "id",
            "code",
            "asset_number",
            "description",
            "operational_state",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "operational_state",
            "created_at",
            "updated_at",
        ]


class ComputerCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Computer
        fields = [
            "id",
            "code",
            "asset_number",
            "description",
            "operational_state",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ComputerOperationalStateSerializer(serializers.Serializer):
    operational_state = serializers.ChoiceField(
        choices=Computer.OperationalState.choices,
    )
    reason = serializers.CharField(required=False, allow_blank=True)


class ActiveSessionStateImpactSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=["REALLOCATED", "FINISHED"])
    from_computer_id = serializers.IntegerField()
    to_computer_id = serializers.IntegerField(allow_null=True)


class ReallocatedReservationImpactSerializer(serializers.Serializer):
    reservation_id = serializers.IntegerField()
    from_computer_id = serializers.IntegerField()
    to_computer_id = serializers.IntegerField()


class CancelledReservationImpactSerializer(serializers.Serializer):
    reservation_id = serializers.IntegerField()


class ReservationStateImpactSerializer(serializers.Serializer):
    reallocated = ReallocatedReservationImpactSerializer(many=True)
    cancelled = CancelledReservationImpactSerializer(many=True)


class ComputerStateImpactSerializer(serializers.Serializer):
    active_session = ActiveSessionStateImpactSerializer(allow_null=True)
    reservations = ReservationStateImpactSerializer()


class ComputerOperationalStateResponseSerializer(serializers.Serializer):
    computer = ComputerSerializer()
    impact = ComputerStateImpactSerializer()


class AvailabilityDateQuerySerializer(serializers.Serializer):
    date = serializers.DateField()


class AvailabilitySlotSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    effective_status = serializers.ChoiceField(choices=EFFECTIVE_STATUS_CHOICES)
    reserved_by_current_user = serializers.BooleanField()
    selectable = serializers.BooleanField()


class NextAvailableSlotSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class ImmediateUsageSerializer(serializers.Serializer):
    can_start_now = serializers.BooleanField()
    max_planned_ends_at = serializers.DateTimeField(allow_null=True)
    limited_by = serializers.ChoiceField(
        choices=IMMEDIATE_USAGE_LIMIT_CHOICES,
        allow_null=True,
    )


class ImmediateUsageDetailSerializer(ImmediateUsageSerializer):
    planned_end_options = serializers.ListField(child=serializers.DateTimeField())


class ComputerAvailabilityItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    description = serializers.CharField()
    operational_state = serializers.ChoiceField(
        choices=Computer.OperationalState.choices,
    )
    effective_status_now = serializers.ChoiceField(
        choices=EFFECTIVE_STATUS_CHOICES,
        allow_null=True,
    )
    can_start_now = serializers.BooleanField()
    immediate_usage = ImmediateUsageSerializer()
    available_slot_count = serializers.IntegerField()
    next_available_slot = NextAvailableSlotSerializer(allow_null=True)


class RoomAvailabilitySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ROOM_STATUS_CHOICES)
    source = serializers.ChoiceField(choices=CALENDAR_SOURCE_CHOICES)
    reason = serializers.CharField(allow_blank=True)
    operating_windows = RoomStatusWindowSerializer(many=True)
    active_notices = RoomNoticeSerializer(many=True)


class ComputerAvailabilityResponseSerializer(serializers.Serializer):
    date = serializers.DateField()
    is_today = serializers.BooleanField()
    slot_duration_minutes = serializers.IntegerField()
    generated_at = serializers.DateTimeField()
    room = RoomAvailabilitySerializer()
    computers = ComputerAvailabilityItemSerializer(many=True)


class ComputerSlotsResponseSerializer(serializers.Serializer):
    computer = ComputerSerializer()
    date = serializers.DateField()
    is_today = serializers.BooleanField()
    slot_duration_minutes = serializers.IntegerField()
    immediate_usage = ImmediateUsageDetailSerializer()
    room = RoomAvailabilitySerializer()
    slots = AvailabilitySlotSerializer(many=True)
