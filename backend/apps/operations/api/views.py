from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import HasDemoProfile
from apps.access.services import (
    get_demo_affiliation_type,
    get_demo_institutional_unit,
    get_demo_profile,
    get_demo_user_reference,
)
from apps.computers.models import Computer
from apps.core.enums import DemoProfile
from apps.operations.models import Reservation
from apps.operations.services import cancel_reservation, create_reservation

from .serializers import (
    ReservationCancelSerializer,
    ReservationCreateSerializer,
    ReservationSerializer,
)

OPERATIONAL_PROFILES = [
    DemoProfile.INTERN,
    DemoProfile.LIBRARY_SUPERVISOR,
    DemoProfile.SYSTEM_ADMIN,
]


class ReservationListCreateAPIView(APIView):
    permission_classes = [HasDemoProfile]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            OPERATIONAL_PROFILES
            if self.request.method == "GET"
            else [DemoProfile.ROOM_USER]
        )
        return super().get_permissions()

    @extend_schema(
        responses={200: ReservationSerializer(many=True)}, tags=["reservations"]
    )
    def get(self, request):
        return Response(
            ReservationSerializer(Reservation.objects.all(), many=True).data
        )

    @extend_schema(
        request=ReservationCreateSerializer,
        responses={201: ReservationSerializer},
        tags=["reservations"],
    )
    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        get_object_or_404(Computer, pk=serializer.validated_data["computer_id"])
        reservation = create_reservation(
            **serializer.validated_data,
            user_reference=get_demo_user_reference(request),
            affiliation_type=get_demo_affiliation_type(request),
            institutional_unit=get_demo_institutional_unit(request),
            created_by_profile=get_demo_profile(request),
        )
        return Response(
            ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED
        )


class MyReservationListAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = [DemoProfile.ROOM_USER]

    @extend_schema(
        responses={200: ReservationSerializer(many=True)}, tags=["reservations"]
    )
    def get(self, request):
        reservations = Reservation.objects.filter(
            user_reference=get_demo_user_reference(request)
        )
        return Response(ReservationSerializer(reservations, many=True).data)


class ReservationCancelAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = DemoProfile.values

    @extend_schema(
        request=ReservationCancelSerializer,
        responses={200: ReservationSerializer},
        tags=["reservations"],
    )
    def post(self, request, pk):
        get_object_or_404(Reservation, pk=pk)
        serializer = ReservationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = cancel_reservation(
            reservation_id=pk,
            actor_profile=get_demo_profile(request),
            actor_reference=get_demo_user_reference(request),
            **serializer.validated_data,
        )
        return Response(ReservationSerializer(reservation).data)
