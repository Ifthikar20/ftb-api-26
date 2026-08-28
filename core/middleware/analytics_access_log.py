"""Records every successful authenticated read of a website's analytics.

Mounted after authentication so request.user is resolved. It matches
GET requests under /api/v1/analytics/<website_id>/ that returned a 2xx to an
authenticated user, and appends one row to AnalyticsAccessLog. This is the
audit trail that proves tenant isolation held: the data was only ever read
by the people who own it, and there is a durable, queryable record of each
access.

Design choices:
  - Only logs reads (GET). Writes go through the public pixel endpoint under
    /api/v1/track/ and are out of scope here.
  - Only logs 2xx. A 403/404 from the ownership check means no data was
    returned, so there is nothing to attribute. (Denied attempts are still
    visible in the application audit log stream.)
  - Best-effort: a failure to write the log never breaks the response. The
    customer's dashboard must not 500 because the audit insert hiccuped.
  - Skips the access-log read endpoint itself to avoid recursion / noise.
  - Stores no personal data. The row records the user FOREIGN KEY, not a
    copy of their email, IP address or user agent. Identity is resolved by
    joining when the trail is read, so deleting a user erases them from
    every historical row rather than leaving denormalized copies behind.
"""
from __future__ import annotations

import logging
import re
import uuid

logger = logging.getLogger("apps")

# /api/v1/analytics/<uuid-or-id>/<anything>. Capture the website id segment.
_ANALYTICS_RE = re.compile(r"^/api/v1/analytics/(?P<wid>[^/]+)/")
# Do not log accesses to the access log itself.
_SELF_RE = re.compile(r"^/api/v1/analytics/[^/]+/access-log/?$")


class AnalyticsAccessLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._maybe_log(request, response)
        except Exception:  # never let auditing break the request
            logger.warning("analytics access log failed", exc_info=True)
        return response

    def _maybe_log(self, request, response):
        if request.method != "GET":
            return
        if not (200 <= getattr(response, "status_code", 500) < 300):
            return
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return
        path = request.path
        if _SELF_RE.match(path):
            return
        m = _ANALYTICS_RE.match(path)
        if not m:
            return

        from apps.analytics.models import AnalyticsAccessLog

        wid = m.group("wid")

        # Assign the FK by id rather than fetching the Website first: this
        # runs on every dashboard read, and the row is only reached on a 2xx
        # from a tenant-scoped view, which already proved the website exists
        # and belongs to the caller. Saves one query per request. A
        # non-UUID segment cannot satisfy the FK, so it is left null and
        # website_id_raw carries the original value.
        try:
            website_id = uuid.UUID(str(wid))
        except (ValueError, AttributeError, TypeError):
            website_id = None

        AnalyticsAccessLog.objects.create(
            user=user,
            website_id=website_id,
            website_id_raw=str(wid)[:64],
            path=path[:300],
            method=request.method,
            status_code=response.status_code,
            request_id=str(getattr(request, "request_id", ""))[:64],
        )
