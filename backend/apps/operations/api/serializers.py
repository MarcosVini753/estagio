from rest_framework import serializers

from apps.operations.models import Reservation


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
