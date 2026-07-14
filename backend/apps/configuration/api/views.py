from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import HasDemoProfile
from apps.configuration.models import BookingPolicy, CalendarException, Shift
from apps.configuration.services import update_active_booking_policy
from apps.core.api.errors import ConfigurationRequired
from apps.core.enums import DemoProfile

from .serializers import (
    BookingPolicySerializer,
    BookingPolicyUpdateSerializer,
    CalendarExceptionSerializer,
    ShiftSerializer,
)

READ_PROFILES = DemoProfile.values
MANAGEMENT_PROFILES = [
    DemoProfile.LIBRARY_SUPERVISOR,
    DemoProfile.SYSTEM_ADMIN,
]


class ShiftListCreateAPIView(generics.ListCreateAPIView):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [HasDemoProfile]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()


class ShiftDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [HasDemoProfile]
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()


class CalendarExceptionListCreateAPIView(generics.ListCreateAPIView):
    queryset = CalendarException.objects.all()
    serializer_class = CalendarExceptionSerializer
    permission_classes = [HasDemoProfile]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()


class CalendarExceptionDetailAPIView(generics.RetrieveUpdateAPIView):
    queryset = CalendarException.objects.all()
    serializer_class = CalendarExceptionSerializer
    permission_classes = [HasDemoProfile]
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()


class BookingPolicyAPIView(APIView):
    permission_classes = [HasDemoProfile]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()

    @extend_schema(responses={200: BookingPolicySerializer}, tags=["configuration"])
    def get(self, request):
        policy = (
            BookingPolicy.objects.filter(is_active=True)
            .order_by("-valid_from", "-created_at")
            .first()
        )
        if not policy:
            raise ConfigurationRequired("Nenhuma política de reservas está ativa.")
        return Response(BookingPolicySerializer(policy).data)

    @extend_schema(
        request=BookingPolicyUpdateSerializer,
        responses={200: BookingPolicySerializer},
        tags=["configuration"],
    )
    def patch(self, request):
        serializer = BookingPolicyUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        policy = update_active_booking_policy(values=serializer.validated_data)
        return Response(BookingPolicySerializer(policy).data)
