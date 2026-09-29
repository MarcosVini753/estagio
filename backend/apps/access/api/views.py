from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.permissions import HasAccessAccount
from apps.access.services import (
    authenticate_identifier,
    clear_legacy_demo_context,
)

from .serializers import (
    AuthContextSerializer,
    AuthenticationErrorSerializer,
    LoginSerializer,
)


def auth_context(user):
    account = user.access_account
    return {
        "profile": account.profile,
        "display_name": account.display_name,
        "affiliation_type": account.affiliation_type,
        "institutional_unit": account.institutional_unit,
    }


@method_decorator(csrf_protect, name="dispatch")
class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: AuthContextSerializer,
            400: AuthenticationErrorSerializer,
            403: None,
        },
        tags=["authentication"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_identifier(
            request._request,
            serializer.validated_data["identifier"],
            serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {
                    "code": "INVALID_CREDENTIALS",
                    "detail": "CPF/matrícula ou senha inválidos.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        clear_legacy_demo_context(request._request.session)
        login(request._request, user)
        return Response(
            AuthContextSerializer(instance=auth_context(user)).data,
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [HasAccessAccount]

    @extend_schema(request=None, responses={204: None}, tags=["authentication"])
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthContextAPIView(APIView):
    permission_classes = [HasAccessAccount]

    @extend_schema(responses={200: AuthContextSerializer}, tags=["authentication"])
    def get(self, request):
        return Response(AuthContextSerializer(instance=auth_context(request.user)).data)
