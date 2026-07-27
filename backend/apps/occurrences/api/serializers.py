from rest_framework import serializers

from apps.occurrences.models import Occurrence


class OccurrenceSerializer(serializers.ModelSerializer):
    computer_id = serializers.IntegerField(read_only=True)
    session_id = serializers.IntegerField(read_only=True)
    allocation_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Occurrence
        fields = [
            "id",
            "reported_by_reference",
            "computer_id",
            "session_id",
            "allocation_id",
            "description",
            "status",
            "resolved_by_profile",
            "resolution_notes",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OccurrenceCreateSerializer(serializers.Serializer):
    computer_id = serializers.IntegerField(min_value=1, required=False)
    session_id = serializers.IntegerField(min_value=1, required=False)
    allocation_id = serializers.IntegerField(min_value=1, required=False)
    description = serializers.CharField(max_length=5000, trim_whitespace=True)


class OccurrenceUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Occurrence.Status.choices)
    resolution_notes = serializers.CharField(
        max_length=5000,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
