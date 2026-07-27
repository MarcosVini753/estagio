from rest_framework import serializers

from apps.core.enums import AffiliationType
from apps.operations.models import ComputerAllocation, Reservation, UseSession


class ReservationSerializer(serializers.ModelSerializer):
    computer_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "computer_id",
            "user_reference",
            "affiliation_type",
            "institutional_unit",
            "starts_at",
            "ends_at",
            "status",
            "created_by_profile",
            "cancelled_by_profile",
            "cancelled_at",
            "cancellation_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ReservationCreateSerializer(serializers.Serializer):
    computer_id = serializers.IntegerField(min_value=1)
    starts_at = serializers.DateTimeField()


class ReservationCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class ComputerAllocationSerializer(serializers.ModelSerializer):
    computer_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ComputerAllocation
        fields = [
            "id",
            "computer_id",
            "sequence",
            "started_at",
            "ended_at",
            "end_reason",
            "switch_reason",
        ]


class UseSessionSerializer(serializers.ModelSerializer):
    reservation_id = serializers.IntegerField(read_only=True)
    start_shift_id = serializers.IntegerField(read_only=True)
    allocations = ComputerAllocationSerializer(many=True, read_only=True)

    class Meta:
        model = UseSession
        fields = [
            "id",
            "user_reference",
            "affiliation_type",
            "institutional_unit",
            "reservation_id",
            "started_at",
            "ended_at",
            "status",
            "start_shift_id",
            "entry_recorded_by_profile",
            "exit_recorded_by_profile",
            "allocations",
        ]


class UsageSessionStartSerializer(serializers.Serializer):
    computer_id = serializers.IntegerField(min_value=1)
    reservation_id = serializers.IntegerField(min_value=1, required=False)
    user_reference = serializers.CharField(max_length=100, required=False)
    affiliation_type = serializers.ChoiceField(
        choices=AffiliationType.choices,
        required=False,
    )
    institutional_unit = serializers.CharField(max_length=255, required=False)


class ComputerSwitchSerializer(serializers.Serializer):
    computer_id = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class UsageSessionFinishSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)
