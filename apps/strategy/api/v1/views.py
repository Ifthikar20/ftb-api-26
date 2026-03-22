from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.strategy.api.v1.serializers import (
    ActionSerializer,
    ChatMessageSerializer,
    ContentCalendarEntrySerializer,
    MorningBriefSerializer,
    StrategyListSerializer,
    StrategySerializer,
)
from apps.strategy.models import Strategy
from apps.strategy.services.action_service import ActionService
from apps.strategy.services.calendar_service import CalendarService
from apps.strategy.services.chat_service import ChatService
from apps.strategy.services.morning_brief_service import MorningBriefService
from apps.strategy.services.prediction_service import PredictionService
from apps.websites.services.website_service import WebsiteService
from core.exceptions import ResourceNotFound
from core.interceptors.throttling import AIGenerationThrottle


class GenerateStrategyView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIGenerationThrottle]

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        plan_type = request.data.get("plan_type", "30")
        from apps.strategy.tasks import generate_strategy_async
        generate_strategy_async.delay(str(website.id), plan_type)
        return Response({"message": "Strategy generation started."}, status=status.HTTP_202_ACCEPTED)


class CurrentStrategyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        strategy = Strategy.objects.filter(website_id=website_id, status="active").first()
        if not strategy:
            raise ResourceNotFound("No active strategy found.")
        return Response(StrategySerializer(strategy).data)


class StrategyHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        strategies = Strategy.objects.filter(website_id=website_id)
        return Response(StrategyListSerializer(strategies, many=True).data)


class ActionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        actions = ActionService.get_this_weeks_actions(website_id=website_id)
        return Response(ActionSerializer(actions, many=True).data)


class ActionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, website_id, action_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        new_status = request.data.get("status")
        action = ActionService.update_action_status(
            action_id=action_id, website_id=website_id, status=new_status, user=request.user
        )
        return Response(ActionSerializer(action).data)


class CalendarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        month = request.query_params.get("month")
        entries = CalendarService.get_entries(website_id=website_id, month=month)
        return Response(ContentCalendarEntrySerializer(entries, many=True).data)


class ChatView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AIGenerationThrottle]

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        content = request.data.get("message", "")
        if not content:
            return Response({"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST)
        reply = ChatService.send_message(website=website, user=request.user, content=content)
        return Response(ChatMessageSerializer(reply).data)


class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        history = ChatService.get_history(website_id=website_id)
        return Response(history)

    def delete(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        ChatService.clear_history(website=website, user=request.user)
        return Response({"message": "History cleared."})


class MorningBriefView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        brief = MorningBriefService.generate_brief(website=website)
        return Response(MorningBriefSerializer(brief).data)


class PredictionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        WebsiteService.get_for_user(user=request.user, website_id=website_id)
        data = PredictionService.get_projections(website_id=website_id)
        return Response(data)
