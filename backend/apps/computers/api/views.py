from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import HasDemoProfile
from apps.access.services import get_demo_profile, get_demo_user_reference
from apps.computers.models import Computer
from apps.computers.services import change_operational_state
from apps.core.enums import DemoProfile
from apps.operations.availability import (
    get_computer_slots,
    get_computers_availability,
)

from .serializers import (
    AvailabilityDateQuerySerializer,
    ComputerAvailabilityResponseSerializer,
    ComputerCreateSerializer,
    ComputerOperationalStateSerializer,
    ComputerSerializer,
    ComputerSlotsResponseSerializer,
)

READ_PROFILES = DemoProfile.values
MANAGEMENT_PROFILES = [
    DemoProfile.LIBRARY_SUPERVISOR,
    DemoProfile.SYSTEM_ADMIN,
]
OPERATIONAL_STATE_PROFILES = [
    DemoProfile.INTERN,
    DemoProfile.LIBRARY_SUPERVISOR,
    DemoProfile.SYSTEM_ADMIN,
]


class ComputerListCreateAPIView(generics.ListCreateAPIView):
    queryset = Computer.objects.all()
    permission_classes = [HasDemoProfile]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ComputerCreateSerializer
        return ComputerSerializer


class ComputerDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Computer.objects.all()
    serializer_class = ComputerSerializer
    permission_classes = [HasDemoProfile]
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()


class ComputerOperationalStateAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = OPERATIONAL_STATE_PROFILES

    @extend_schema(
        request=ComputerOperationalStateSerializer,
        responses={200: ComputerSerializer},
        tags=["computers"],
    )
    def patch(self, request, pk):
        get_object_or_404(Computer, pk=pk)
        serializer = ComputerOperationalStateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        computer = change_operational_state(
            computer_id=pk,
            new_state=serializer.validated_data["operational_state"],
            actor_profile=get_demo_profile(request),
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(ComputerSerializer(computer).data)


class ComputerAvailabilityAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = READ_PROFILES

    @extend_schema(
        parameters=[AvailabilityDateQuerySerializer],
        responses={200: ComputerAvailabilityResponseSerializer},
        tags=["availability"],
    )
    def get(self, request):
        query = AvailabilityDateQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        payload, _ = get_computers_availability(
            target_date=query.validated_data["date"],
            computers=Computer.objects.all(),
            user_reference=get_demo_user_reference(request),
        )
        return Response(payload)


class ComputerSlotsAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = READ_PROFILES

    @extend_schema(
        parameters=[AvailabilityDateQuerySerializer],
        responses={200: ComputerSlotsResponseSerializer},
        tags=["availability"],
    )
    def get(self, request, pk):
        query = AvailabilityDateQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        computer = get_object_or_404(Computer, pk=pk)
        payload = get_computer_slots(
            target_date=query.validated_data["date"],
            computer=computer,
            user_reference=get_demo_user_reference(request),
        )
        payload["computer"] = ComputerSerializer(computer).data
        return Response(payload)
