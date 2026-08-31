"""Internal ops API — consumed ONLY by the ftb-min admin server.

Gated by the ``X-Admin-Key`` header against ``settings.ADMIN_OPS_KEY``.
An empty setting disables the surface entirely, and every failure mode
is a 404 — to anyone probing without the key these endpoints are
indistinguishable from routes that do not exist. The admin server holds
the key server-side and proxies for its UI; browsers never see it. In
production, additionally restrict this path prefix to the admin host at
the network layer (reverse proxy / firewall).

Read-only by design: the admin dashboard observes; it does not mutate
tenant data.
"""

import ipaddress
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import RateLimited, ResourceNotFound
from core.logging.audit_logger import audit_log


class InternalAdminView(APIView):
    """Base gate for the internal ops surface. Three independent checks,
    all failing as 404 so the endpoints are unenumerable:

      1. Source IP inside ADMIN_OPS_ALLOWED_CIDRS ("only from that
         server"). REMOTE_ADDR is used — never a forwarded header, which
         any caller can forge. Empty list = the surface is OFF.
      2. Constant-time X-Admin-Key match. Empty key = OFF.
      3. Per-IP token-bucket rate limit.

    Every request is additionally audit-logged (path + source IP) on top
    of the middleware's request log. No JWT/session auth is involved.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    # In-process sliding window: fail-closed by construction (no cache /
    # Redis dependency that could fail open on an auth-adjacent control).
    # One admin server talks to one worker set; per-process is fine.
    _WINDOW_S = 60
    _MAX_PER_WINDOW = 120
    _requests: dict = defaultdict(deque)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        ip = request.META.get("REMOTE_ADDR", "") or ""
        cidrs = getattr(settings, "ADMIN_OPS_ALLOWED_CIDRS", []) or []
        try:
            addr = ipaddress.ip_address(ip)
            ip_ok = any(
                addr in ipaddress.ip_network(c, strict=False) for c in cidrs
            )
        except ValueError:
            ip_ok = False
        if not ip_ok:
            raise ResourceNotFound("Not found.")

        key = getattr(settings, "ADMIN_OPS_KEY", "") or ""
        supplied = request.headers.get("X-Admin-Key", "") or ""
        # Compare as bytes: compare_digest on str raises on non-ASCII,
        # which would 500 and stand out from the uniform 404s.
        if not key or not secrets.compare_digest(
            supplied.encode("utf-8", "replace"), key.encode("utf-8", "replace"),
        ):
            audit_log(
                "admin_ops.denied", action="read",
                metadata={"path": request.path, "ip": ip}, success=False,
            )
            raise ResourceNotFound("Not found.")

        now = time.monotonic()
        window = self._requests[ip]
        while window and now - window[0] > self._WINDOW_S:
            window.popleft()
        if len(window) >= self._MAX_PER_WINDOW:
            raise RateLimited()
        window.append(now)

        audit_log(
            "admin_ops.request", action="read",
            metadata={"path": request.path, "ip": ip},
        )


class AdminOverviewView(InternalAdminView):
    """Headline numbers for the admin Overview tab."""

    def get(self, request):
        from apps.accounts.models import User
        from apps.billing.models import Subscription
        from apps.llm_ranking.models import LLMRankingAudit
        from apps.websites.models import Website
        from core.utils.constants import SubscriptionStatus

        now = timezone.now()
        week = now - timedelta(days=7)
        month = now - timedelta(days=30)

        users = User.objects.all()
        subs = Subscription.objects.all()
        audits = LLMRankingAudit.objects.all()

        return Response({
            "users": {
                "total": users.count(),
                "new_7d": users.filter(created_at__gte=week).count(),
                "new_30d": users.filter(created_at__gte=month).count(),
                "verified": users.filter(is_email_verified=True).count(),
            },
            "subscriptions": {
                "active": subs.filter(status=SubscriptionStatus.ACTIVE).count(),
                "trialing": subs.filter(status=SubscriptionStatus.TRIALING).count(),
                "past_due": subs.filter(status=SubscriptionStatus.PAST_DUE).count(),
                "canceled": subs.filter(status=SubscriptionStatus.CANCELED).count(),
            },
            "projects": {"total": Website.objects.count()},
            "audits": {
                "total": audits.count(),
                "last_7d": audits.filter(created_at__gte=week).count(),
            },
            "ai_usage": _ai_usage_totals(month),
            "generated_at": now.isoformat(),
        })


def _ai_usage_totals(since):
    from django.db.models import Sum

    from apps.accounts.models import AITokenUsage

    qs = AITokenUsage.objects.filter(created_at__gte=since)
    agg = qs.aggregate(tokens=Sum("total_tokens"), cost=Sum("estimated_cost_usd"))
    return {
        "tokens_30d": int(agg["tokens"] or 0),
        "cost_30d_usd": float(agg["cost"] or 0),
    }


def _page_enrichment(user_ids):
    """Per-user rollups for one page of the directory, computed as a few
    grouped queries over the page's ids — no join multiplication, no N+1."""
    from django.db.models import Count, Sum

    from apps.accounts.models import AITokenUsage
    from apps.llm_ranking.models import LLMRankingAudit
    from apps.prompt_library.models import BrandPrompt
    from apps.websites.models import Integration, Website

    tokens = {
        row["user_id"]: row
        for row in AITokenUsage.objects.filter(user_id__in=user_ids)
        .values("user_id")
        .annotate(tokens=Sum("total_tokens"), cost=Sum("estimated_cost_usd"))
    }
    prompts = {
        row["website__user_id"]: row["n"]
        for row in BrandPrompt.objects.filter(website__user_id__in=user_ids)
        .values("website__user_id")
        .annotate(n=Count("id"))
    }
    audits = {
        row["created_by_id"]: row["n"]
        for row in LLMRankingAudit.objects.filter(created_by_id__in=user_ids)
        .values("created_by_id")
        .annotate(n=Count("id"))
    }
    integrations: dict = {}
    for row in (
        Integration.objects
        .filter(website__user_id__in=user_ids, is_active=True)
        .values_list("website__user_id", "type")
    ):
        integrations.setdefault(row[0], set()).add(row[1])
    for uid in (
        Website.objects
        .filter(user_id__in=user_ids, pixel_verified=True)
        .values_list("user_id", flat=True)
    ):
        integrations.setdefault(uid, set()).add("pixel")

    def build(uid):
        t = tokens.get(uid) or {}
        return {
            "prompts": prompts.get(uid, 0),
            "audits": audits.get(uid, 0),
            "tokens_total": int(t.get("tokens") or 0),
            "ai_cost_usd": float(t.get("cost") or 0),
            "integrations": sorted(integrations.get(uid, set())),
        }

    return build


class AdminUsersView(InternalAdminView):
    """Paginated user directory for the admin Users tab."""

    def get(self, request):
        from apps.accounts.models import User
        from apps.billing.models import Subscription
        from apps.billing.services.plan_limits import plan_for_subscription

        qs = (
            User.objects
            .select_related("subscription")
            .annotate(
                projects_count=Count(
                    "websites", filter=Q(websites__is_deleted=False),
                ),
            )
            .order_by("-created_at")
        )
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(email__icontains=search) | Q(full_name__icontains=search),
            )
        try:
            limit = min(max(int(request.query_params.get("limit", 50)), 1), 200)
            offset = max(int(request.query_params.get("offset", 0)), 0)
        except (TypeError, ValueError):
            limit, offset = 50, 0

        total = qs.count()
        page = list(qs[offset:offset + limit])
        enrich = _page_enrichment([u.id for u in page])
        rows = []
        for user in page:
            try:
                sub = user.subscription
            except Subscription.DoesNotExist:
                sub = None
            rows.append({
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "plan": str(plan_for_subscription(sub)),
                "subscription_status": sub.status if sub else None,
                "projects": user.projects_count,
                "verified": user.is_email_verified,
                "joined": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                **enrich(user.id),
            })
        return Response({"total": total, "limit": limit, "offset": offset, "rows": rows})
