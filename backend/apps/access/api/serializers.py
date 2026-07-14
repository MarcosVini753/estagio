from rest_framework import serializers

from apps.core.enums import DemoProfile


class DemoProfileSelectionSerializer(serializers.Serializer):
    profile = serializers.ChoiceField(choices=DemoProfile.choices)
