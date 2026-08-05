from rest_framework import serializers

from apps.core.enums import AffiliationType, DemoProfile


class DemoProfileSelectionSerializer(serializers.Serializer):
    profile = serializers.ChoiceField(choices=DemoProfile.choices)
    user_reference = serializers.CharField(
        max_length=100, required=False, trim_whitespace=True
    )
    affiliation_type = serializers.ChoiceField(
        choices=AffiliationType.choices,
        required=False,
    )
    institutional_unit = serializers.CharField(
        max_length=255,
        required=False,
        trim_whitespace=True,
    )

    def validate(self, attrs):
        profile = attrs["profile"]
        identity_fields = (
            "user_reference",
            "affiliation_type",
            "institutional_unit",
        )
        if profile == DemoProfile.ROOM_USER:
            missing = [field for field in identity_fields if not attrs.get(field)]
            if missing:
                raise serializers.ValidationError(
                    {
                        field: "Este campo é obrigatório para Usuário da Sala."
                        for field in missing
                    }
                )
            if attrs["affiliation_type"] == AffiliationType.NOT_INFORMED:
                raise serializers.ValidationError(
                    {"affiliation_type": "Selecione um vínculo informado."}
                )
        elif any(field in attrs for field in identity_fields):
            raise serializers.ValidationError(
                "A identidade acadêmica é exclusiva do perfil Usuário da Sala."
            )
        return attrs
