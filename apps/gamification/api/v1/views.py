from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from apps.gamification.services import (
    is_gamification_enabled,
    get_user_progress,
    get_card_collection,
)


def _check_enabled(func):
    """Decorator: return 404 if gamification is disabled."""
    def wrapper(request, *args, **kwargs):
        if not is_gamification_enabled():
            return Response(
                {"detail": "Gamification is not enabled."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return func(request, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@_check_enabled
def progress_view(request):
    """GET /api/v1/gamification/progress/"""
    data = get_user_progress(request.user)
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@_check_enabled
def cards_view(request):
    """GET /api/v1/gamification/cards/"""
    cards = get_card_collection(request.user)
    return Response(cards)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@_check_enabled
def feature_status_view(request):
    """GET /api/v1/gamification/status/ — lets frontend know if gamification is on."""
    return Response({"enabled": True})
