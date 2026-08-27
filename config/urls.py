from django.http import JsonResponse
from django.urls import include, path


def health(_: object) -> JsonResponse:
    return JsonResponse({"service": "relay", "status": "ok"})


urlpatterns = [
    path("api/v1/health/", health, name="health"),
    path("api/v1/", include("relay.api.urls")),
]
