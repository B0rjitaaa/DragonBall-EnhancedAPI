from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import ErrorGroup
from .recorder import record_error


class WebErrorSerializer(serializers.Serializer):
    kind = serializers.CharField(max_length=200, default="Error")
    message = serializers.CharField(max_length=2000)
    where = serializers.CharField(max_length=300, allow_blank=True, default="")
    stack = serializers.CharField(max_length=10000, allow_blank=True, default="")
    page = serializers.CharField(max_length=500, allow_blank=True, default="")


class WebErrorView(APIView):
    """POST: la web avisa de un error de JavaScript que ha pasado en el navegador."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "web-errors"

    def post(self, request):
        body = WebErrorSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        e = body.validated_data
        record_error(ErrorGroup.Source.WEB, e["kind"], e["message"], e["where"] or e["message"][:300], e["stack"],
                     request=e["page"], user_agent=request.META.get("HTTP_USER_AGENT", ""))
        return Response(status=status.HTTP_204_NO_CONTENT)
