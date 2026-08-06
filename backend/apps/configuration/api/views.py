from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import HasDemoProfile
from apps.access.services import get_demo_profile
from apps.configuration.calendar import room_status_payload
from apps.configuration.models import (
    BookingPolicy,
    CalendarException,
    OperatingSchedule,
    RoomNotice,
    Shift,
)
from apps.configuration.selectors import get_active_room_notices
from apps.configuration.services import (
    apply_calendar_exception,
    create_operating_schedule,
    create_room_notice,
    preview_operating_schedule_impact,
    replace_operating_schedule,
    replace_shift,
    update_active_booking_policy,
    update_future_operating_schedule,
    update_room_notice,
)
from apps.core.api.errors import ConfigurationRequired
from apps.core.enums import DemoProfile

from .serializers import (
    BookingPolicySerializer,
    BookingPolicyUpdateSerializer,
    CalendarExceptionSerializer,
    OperatingScheduleCreateSerializer,
    OperatingScheduleImpactResponseSerializer,
    OperatingScheduleImpactSerializer,
    OperatingScheduleReplaceSerializer,
    OperatingScheduleSerializer,
    OperatingScheduleUpdateSerializer,
    RoomNoticeCreateSerializer,
    RoomNoticeSerializer,
    RoomNoticeUpdateSerializer,
    RoomStatusQuerySerializer,
    RoomStatusSerializer,
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


class CalendarExceptionListCreateAPIView(APIView):
    permission_classes = [HasDemoProfile]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()

    @extend_schema(
        responses={200: CalendarExceptionSerializer(many=True)},
        tags=["configuration"],
    )
    def get(self, request):
        return Response(
            CalendarExceptionSerializer(CalendarException.objects.all(), many=True).data
        )

    @extend_schema(
        request=CalendarExceptionSerializer,
        responses={201: CalendarExceptionSerializer},
        tags=["configuration"],
    )
    def post(self, request):
        serializer = CalendarExceptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        confirm_invalidation = values.pop("confirm_invalidation", False)
        notify_users = values.pop("notify_users", False)
        notice = values.pop("notice", None)
        exception = apply_calendar_exception(
            values=values,
            actor_profile=get_demo_profile(request),
            confirm_invalidation=confirm_invalidation,
            notify_users=notify_users,
            notice=notice,
        )
        return Response(
            CalendarExceptionSerializer(exception).data,
            status=status.HTTP_201_CREATED,
        )


class CalendarExceptionDetailAPIView(APIView):
    permission_classes = [HasDemoProfile]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()

    @extend_schema(
        responses={200: CalendarExceptionSerializer},
        tags=["configuration"],
    )
    def get(self, request, pk):
        exception = get_object_or_404(CalendarException, pk=pk)
        return Response(CalendarExceptionSerializer(exception).data)

    @extend_schema(
        request=CalendarExceptionSerializer,
        responses={200: CalendarExceptionSerializer},
        tags=["configuration"],
    )
    def patch(self, request, pk):
        exception = get_object_or_404(CalendarException, pk=pk)
        serializer = CalendarExceptionSerializer(
            exception,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        confirm_invalidation = values.pop("confirm_invalidation", False)
        notify_users = values.pop("notify_users", False)
        notice = values.pop("notice", None)
        exception = apply_calendar_exception(
            exception_id=pk,
            values=values,
            actor_profile=get_demo_profile(request),
            confirm_invalidation=confirm_invalidation,
            notify_users=notify_users,
            notice=notice,
        )
        return Response(CalendarExceptionSerializer(exception).data)


class OperatingScheduleListCreateAPIView(APIView):
    permission_classes = [HasDemoProfile]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()

    @extend_schema(
        responses={200: OperatingScheduleSerializer(many=True)},
        tags=["configuration"],
    )
    def get(self, request):
        schedules = OperatingSchedule.objects.prefetch_related("days__windows")
        return Response(OperatingScheduleSerializer(schedules, many=True).data)

    @extend_schema(
        request=OperatingScheduleCreateSerializer,
        responses={201: OperatingScheduleSerializer},
        tags=["configuration"],
    )
    def post(self, request):
        serializer = OperatingScheduleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = create_operating_schedule(
            actor_profile=get_demo_profile(request),
            **serializer.validated_data,
        )
        return Response(
            OperatingScheduleSerializer(schedule).data,
            status=status.HTTP_201_CREATED,
        )


class OperatingScheduleDetailAPIView(APIView):
    permission_classes = [HasDemoProfile]

    def get_permissions(self):
        self.allowed_demo_profiles = (
            READ_PROFILES if self.request.method == "GET" else MANAGEMENT_PROFILES
        )
        return super().get_permissions()

    @extend_schema(
        responses={200: OperatingScheduleSerializer},
        tags=["configuration"],
    )
    def get(self, request, pk):
        schedule = get_object_or_404(
            OperatingSchedule.objects.prefetch_related("days__windows"),
            pk=pk,
        )
        return Response(OperatingScheduleSerializer(schedule).data)

    @extend_schema(
        request=OperatingScheduleUpdateSerializer,
        responses={200: OperatingScheduleSerializer},
        tags=["configuration"],
    )
    def patch(self, request, pk):
        get_object_or_404(OperatingSchedule, pk=pk)
        serializer = OperatingScheduleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        confirm_invalidation = values.pop("confirm_invalidation", False)
        schedule = update_future_operating_schedule(
            schedule_id=pk,
            values=values,
            actor_profile=get_demo_profile(request),
            confirm_invalidation=confirm_invalidation,
        )
        return Response(OperatingScheduleSerializer(schedule).data)


class OperatingScheduleReplaceAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = MANAGEMENT_PROFILES

    @extend_schema(
        request=OperatingScheduleReplaceSerializer,
        responses={201: OperatingScheduleSerializer},
        tags=["configuration"],
    )
    def post(self, request, pk):
        get_object_or_404(OperatingSchedule, pk=pk)
        serializer = OperatingScheduleReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = replace_operating_schedule(
            schedule_id=pk,
            actor_profile=get_demo_profile(request),
            **serializer.validated_data,
        )
        return Response(
            OperatingScheduleSerializer(schedule).data,
            status=status.HTTP_201_CREATED,
        )


class OperatingScheduleImpactPreviewAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = MANAGEMENT_PROFILES

    @extend_schema(
        request=OperatingScheduleImpactSerializer,
        responses={200: OperatingScheduleImpactResponseSerializer},
        tags=["configuration"],
    )
    def post(self, request):
        serializer = OperatingScheduleImpactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("name", None)
        data.pop("reason", None)
        return Response(preview_operating_schedule_impact(**data))


class RoomStatusAPIView(APIView):
    permission_classes = []

    @extend_schema(
        parameters=[RoomStatusQuerySerializer],
        responses={200: RoomStatusSerializer},
        tags=["configuration"],
    )
    def get(self, request):
        query = RoomStatusQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(room_status_payload(query.validated_data["date"]))


class ActiveRoomNoticeListAPIView(APIView):
    permission_classes = []

    @extend_schema(
        responses={200: RoomNoticeSerializer(many=True)},
        tags=["configuration"],
    )
    def get(self, request):
        return Response(RoomNoticeSerializer(get_active_room_notices(), many=True).data)


class RoomNoticeListCreateAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = MANAGEMENT_PROFILES

    @extend_schema(
        responses={200: RoomNoticeSerializer(many=True)},
        tags=["configuration"],
    )
    def get(self, request):
        return Response(RoomNoticeSerializer(RoomNotice.objects.all(), many=True).data)

    @extend_schema(
        request=RoomNoticeCreateSerializer,
        responses={201: RoomNoticeSerializer},
        tags=["configuration"],
    )
    def post(self, request):
        serializer = RoomNoticeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notice = create_room_notice(
            values=serializer.validated_data,
            actor_profile=get_demo_profile(request),
        )
        return Response(
            RoomNoticeSerializer(notice).data,
            status=status.HTTP_201_CREATED,
        )


class RoomNoticeDetailAPIView(APIView):
    permission_classes = [HasDemoProfile]
    allowed_demo_profiles = MANAGEMENT_PROFILES

    @extend_schema(
        responses={200: RoomNoticeSerializer},
        tags=["configuration"],
    )
    def get(self, request, pk):
        notice = get_object_or_404(RoomNotice, pk=pk)
        return Response(RoomNoticeSerializer(notice).data)

    @extend_schema(
        request=RoomNoticeUpdateSerializer,
        responses={200: RoomNoticeSerializer},
        tags=["configuration"],
    )
    def patch(self, request, pk):
        get_object_or_404(RoomNotice, pk=pk)
        serializer = RoomNoticeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notice = update_room_notice(
            notice_id=pk,
            values=serializer.validated_data,
            actor_profile=get_demo_profile(request),
        )
        return Response(RoomNoticeSerializer(notice).data)


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
