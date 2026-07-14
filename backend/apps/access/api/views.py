from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.enums import DemoProfile
from apps.access.services import get_demo_profile, select_demo_profile

from .serializers import DemoProfileSelectionSerializer


def profiles_payload():
    return [{"value": value, "label": label} for value, label in DemoProfile.choices]


class DemoContextAPIView(APIView):
    @extend_schema(responses={200: dict}, tags=["demo"])
    def get(self, request):
        return Response(
            {
                "profile": get_demo_profile(request),
                "available_profiles": profiles_payload(),
                "warning": "Autorização simulada; não representa autenticação ou identidade real.",
            }
        )


class DemoSelectProfileAPIView(APIView):
    @extend_schema(
        request=DemoProfileSelectionSerializer,
        responses={200: dict},
        tags=["demo"],
    )
    def post(self, request):
        serializer = DemoProfileSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = select_demo_profile(request, serializer.validated_data["profile"])
        return Response(
            {
                "profile": profile,
                "warning": "Perfil selecionado apenas para demonstração.",
            },
            status=status.HTTP_200_OK,
        )
