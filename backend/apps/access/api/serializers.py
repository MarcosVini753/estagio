from rest_framework import serializers

from apps.access.models import AccessAccount
from apps.core.enums import AffiliationType


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=150, trim_whitespace=True)
    password = serializers.CharField(
        max_length=128, write_only=True, trim_whitespace=False
    )


class AuthenticationErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()


class AuthContextSerializer(serializers.Serializer):
    profile = serializers.ChoiceField(choices=AccessAccount.PROFILE_CHOICES)
    display_name = serializers.CharField()
    affiliation_type = serializers.ChoiceField(
        choices=AffiliationType.choices,
        allow_null=True,
    )
    institutional_unit = serializers.CharField(allow_blank=True)
