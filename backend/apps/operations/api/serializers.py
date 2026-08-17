from rest_framework import serializers

from apps.core.enums import AffiliationType
from apps.operations.models import ComputerAllocation, Reservation, UseSession


class ReservationSerializer(serializers.ModelSerializer):
    computer_id = serializers.IntegerField(read_only=True)
    booking_policy_id = serializers.IntegerField(read_only=True)
    slot_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "computer_id",
            "booking_policy_id",
            "user_reference",
            "affiliation_type",
            "institutional_unit",
            "starts_at",
            "ends_at",
            "slot_count",
            "check_in_deadline_at",
            "exit_deadline_at",
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
    slot_count = serializers.IntegerField(min_value=1)


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
    slot_count = serializers.IntegerField(read_only=True)
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
            "planned_starts_at",
            "planned_ends_at",
            "exit_deadline_at",
            "slot_count",
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
    slot_count = serializers.IntegerField(min_value=1, required=False)
    user_reference = serializers.CharField(max_length=100, required=False)
    affiliation_type = serializers.ChoiceField(
        choices=AffiliationType.choices,
        required=False,
    )
    institutional_unit = serializers.CharField(max_length=255, required=False)

    def validate(self, attrs):
        reservation_id = attrs.get("reservation_id")
        slot_count = attrs.get("slot_count")
        if reservation_id is not None and slot_count is not None:
            raise serializers.ValidationError(
                {"slot_count": "A duração é definida pela reserva informada."}
            )
        if reservation_id is None and slot_count is None:
            raise serializers.ValidationError(
                {"slot_count": "Informe a quantidade de slots para uso imediato."}
            )
        return attrs


class ComputerSwitchSerializer(serializers.Serializer):
    computer_id = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class UsageSessionFinishSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class UsageSessionCorrectionSerializer(serializers.Serializer):
    started_at = serializers.DateTimeField(required=False)
    ended_at = serializers.DateTimeField(required=False)
    last_allocation_started_at = serializers.DateTimeField(required=False)
    last_allocation_ended_at = serializers.DateTimeField(required=False)
    reason = serializers.CharField(max_length=2000, trim_whitespace=True)

    def validate(self, attrs):
        correction_fields = {
            "started_at",
            "ended_at",
            "last_allocation_started_at",
            "last_allocation_ended_at",
        }
        if not correction_fields.intersection(attrs):
            raise serializers.ValidationError(
                "Informe ao menos um horário para correção."
            )
        return attrs
