from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthAPIView(APIView):
    @extend_schema(responses={200: dict}, tags=["system"])
    def get(self, request):
        return Response(
            {"status": "ok", "service": "biblioteca-ufac-api", "version": "v1"}
        )
