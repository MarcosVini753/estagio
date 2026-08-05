from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import HasDemoProfile
from apps.access.services import get_demo_profile, get_demo_user_reference
from apps.computers.models import Computer
from apps.core.enums import DemoProfile
from apps.occurrences.models import Occurrence
from apps.occurrences.services import create_occurrence, transition_occurrence
from apps.operations.models import ComputerAllocation, UseSession

from .serializers import (
    OccurrenceCreateSerializer,
    OccurrenceSerializer,
    OccurrenceUpdateSerializer,
)

OPERATIONAL_PROFILES = [
    DemoProfile.INTERN,
    DemoProfile.LIBRARY_SUPERVISOR,
    DemoProfile.SYSTEM_ADMIN,
]


def _visible_occurrences(request):
    occurrences = Occurrence.objects.all()
    if get_demo_profile(request) == DemoProfile.ROOM_USER:
        occurrences = occurrences.filter(
            reported_by_reference=get_demo_user_reference(request)
        )
    return occurrences


class OccurrenceListCreateAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = DemoProfile.values

    @extend_schema(
        responses={200: OccurrenceSerializer(many=True)}, tags=["occurrences"]
    )
    def get(self, request):
        return Response(
            OccurrenceSerializer(_visible_occurrences(request), many=True).data
        )

    @extend_schema(
        request=OccurrenceCreateSerializer,
        responses={201: OccurrenceSerializer},
        tags=["occurrences"],
    )
    def post(self, request):
        serializer = OccurrenceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        occurrence = create_occurrence(
            actor_profile=get_demo_profile(request),
            actor_reference=get_demo_user_reference(request),
            description=data["description"],
            computer=(
                get_object_or_404(Computer, pk=data["computer_id"])
                if data.get("computer_id")
                else None
            ),
            session=(
                get_object_or_404(UseSession, pk=data["session_id"])
                if data.get("session_id")
                else None
            ),
            allocation=(
                get_object_or_404(ComputerAllocation, pk=data["allocation_id"])
                if data.get("allocation_id")
                else None
            ),
        )
        return Response(
            OccurrenceSerializer(occurrence).data,
            status=status.HTTP_201_CREATED,
        )


class OccurrenceDetailAPIView(APIView):
    permission_classes = [HasDemoProfile]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            OPERATIONAL_PROFILES
            if self.request.method == "PATCH"
            else DemoProfile.values
        )
        return super().get_permissions()

    @extend_schema(responses={200: OccurrenceSerializer}, tags=["occurrences"])
    def get(self, request, pk):
        occurrence = get_object_or_404(_visible_occurrences(request), pk=pk)
        return Response(OccurrenceSerializer(occurrence).data)

    @extend_schema(
        request=OccurrenceUpdateSerializer,
        responses={200: OccurrenceSerializer},
        tags=["occurrences"],
    )
    def patch(self, request, pk):
        get_object_or_404(Occurrence, pk=pk)
        serializer = OccurrenceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        occurrence = transition_occurrence(
            occurrence_id=pk,
            actor_profile=get_demo_profile(request),
            **serializer.validated_data,
        )
        return Response(OccurrenceSerializer(occurrence).data)
