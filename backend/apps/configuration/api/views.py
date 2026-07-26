from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import HasDemoProfile
from apps.access.services import get_demo_profile
from apps.configuration.models import BookingPolicy, CalendarException, Shift
from apps.configuration.services import replace_shift, update_active_booking_policy
from apps.core.api.errors import ConfigurationRequired
from apps.core.enums import DemoProfile

from .serializers import (
    BookingPolicySerializer,
    BookingPolicyUpdateSerializer,
    CalendarExceptionSerializer,
    ShiftReplaceSerializer,
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


class ShiftReplaceAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = MANAGEMENT_PROFILES

    @extend_schema(
        request=ShiftReplaceSerializer,
        responses={201: ShiftSerializer},
        tags=["configuration"],
    )
    def post(self, request, pk):
        get_object_or_404(Shift, pk=pk)
        serializer = ShiftReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shift = replace_shift(
            shift_id=pk,
            actor_profile=get_demo_profile(request),
            **serializer.validated_data,
        )
        return Response(ShiftSerializer(shift).data, status=status.HTTP_201_CREATED)


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
