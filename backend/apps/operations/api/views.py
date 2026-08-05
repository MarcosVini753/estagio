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
from apps.operations.models import Reservation, UseSession
from apps.operations.services import (
    cancel_reservation,
    correct_usage_session,
    create_reservation,
    finish_usage_session,
    start_usage_session,
    switch_computer,
)

from .serializers import (
    ComputerSwitchSerializer,
    ReservationCancelSerializer,
    ReservationCreateSerializer,
    ReservationSerializer,
    UsageSessionCorrectionSerializer,
    UsageSessionFinishSerializer,
    UsageSessionStartSerializer,
    UseSessionSerializer,
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


class CurrentUsageSessionAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = [DemoProfile.ROOM_USER]

    @extend_schema(responses={200: UseSessionSerializer}, tags=["usage-sessions"])
    def get(self, request):
        session = (
            UseSession.objects.filter(
                user_reference=get_demo_user_reference(request),
                status=UseSession.Status.ACTIVE,
            )
            .prefetch_related("allocations")
            .first()
        )
        return Response(UseSessionSerializer(session).data if session else None)


class ActiveUsageSessionListAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = OPERATIONAL_PROFILES

    @extend_schema(
        responses={200: UseSessionSerializer(many=True)}, tags=["usage-sessions"]
    )
    def get(self, request):
        sessions = UseSession.objects.filter(
            status=UseSession.Status.ACTIVE
        ).prefetch_related("allocations")
        return Response(UseSessionSerializer(sessions, many=True).data)


class UsageSessionHistoryAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = DemoProfile.values

    @extend_schema(
        responses={200: UseSessionSerializer(many=True)}, tags=["usage-sessions"]
    )
    def get(self, request):
        sessions = UseSession.objects.exclude(status=UseSession.Status.ACTIVE)
        if get_demo_profile(request) == DemoProfile.ROOM_USER:
            sessions = sessions.filter(user_reference=get_demo_user_reference(request))
        return Response(
            UseSessionSerializer(
                sessions.prefetch_related("allocations"),
                many=True,
            ).data
        )


class UsageSessionStartAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = DemoProfile.values

    @extend_schema(
        request=UsageSessionStartSerializer,
        responses={201: UseSessionSerializer},
        tags=["usage-sessions"],
    )
    def post(self, request):
        serializer = UsageSessionStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        get_object_or_404(Computer, pk=data["computer_id"])
        if reservation_id := data.get("reservation_id"):
            get_object_or_404(Reservation, pk=reservation_id)
        session = start_usage_session(
            computer_id=data["computer_id"],
            reservation_id=reservation_id,
            actor_profile=get_demo_profile(request),
            actor_reference=get_demo_user_reference(request),
            user_reference=data.get("user_reference", get_demo_user_reference(request)),
            affiliation_type=data.get(
                "affiliation_type", get_demo_affiliation_type(request)
            ),
            institutional_unit=data.get(
                "institutional_unit", get_demo_institutional_unit(request)
            ),
        )
        return Response(
            UseSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class UsageSessionSwitchAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = DemoProfile.values

    @extend_schema(
        request=ComputerSwitchSerializer,
        responses={200: UseSessionSerializer},
        tags=["usage-sessions"],
    )
    def post(self, request, pk):
        get_object_or_404(UseSession, pk=pk)
        serializer = ComputerSwitchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        get_object_or_404(Computer, pk=serializer.validated_data["computer_id"])
        session = switch_computer(
            session_id=pk,
            actor_profile=get_demo_profile(request),
            actor_reference=get_demo_user_reference(request),
            **serializer.validated_data,
        )
        return Response(UseSessionSerializer(session).data)


class UsageSessionFinishAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = DemoProfile.values

    @extend_schema(
        request=UsageSessionFinishSerializer,
        responses={200: UseSessionSerializer},
        tags=["usage-sessions"],
    )
    def post(self, request, pk):
        get_object_or_404(UseSession, pk=pk)
        serializer = UsageSessionFinishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = finish_usage_session(
            session_id=pk,
            actor_profile=get_demo_profile(request),
            actor_reference=get_demo_user_reference(request),
            **serializer.validated_data,
        )
        return Response(UseSessionSerializer(session).data)


class UsageSessionCorrectionAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = OPERATIONAL_PROFILES

    @extend_schema(
        request=UsageSessionCorrectionSerializer,
        responses={200: UseSessionSerializer},
        tags=["usage-sessions"],
    )
    def post(self, request, pk):
        get_object_or_404(UseSession, pk=pk)
        serializer = UsageSessionCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = correct_usage_session(
            session_id=pk,
            actor_profile=get_demo_profile(request),
            **serializer.validated_data,
        )
        return Response(UseSessionSerializer(session).data)
