from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.configuration.models import BookingPolicy, CalendarException, Shift


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            "id",
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
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
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


class CalendarExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarException
        fields = [
            "id",
            "date",
            "exception_type",
            "opens_at",
            "closes_at",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
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
        return attrs


class BookingPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingPolicy
        fields = [
            "id",
            "slot_duration_minutes",
            "check_in_tolerance_minutes",
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
    slot_duration_minutes = serializers.IntegerField(min_value=1, required=False)
    check_in_tolerance_minutes = serializers.IntegerField(min_value=0, required=False)
    cancellation_limit_minutes = serializers.IntegerField(min_value=0, required=False)
    max_future_reservations_per_user = serializers.IntegerField(
        min_value=1,
        required=False,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Informe ao menos um campo para atualização.")
        return attrs
