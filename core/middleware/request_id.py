import logging
import re
import time
import uuid

logger = logging.getLogger(__name__)

# Both ids end up in a response header and in log lines: strip anything
# that could smuggle header/log-injection payloads.
_ID_SAFE = re.compile(r"[^a-zA-Z0-9._-]")


class RequestIDMiddleware:
    """
    Assigns a unique X-Request-ID to every request for end-to-end tracing.
    If the client sends one (from Vue.js Axios interceptor), we use it.
    Otherwise we generate one. Included in all log entries and responses.

    Also reads X-Client-Id — a stable per-browser-session id set by the
    frontend — and emits one trace log line per API request carrying both
    ids. Support tickets include the client id, so grepping the app logs
    for it yields exactly that user's requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = _ID_SAFE.sub("", request.META.get("HTTP_X_REQUEST_ID", ""))[:64]
        if not request_id:
            request_id = str(uuid.uuid4())
        client_id = _ID_SAFE.sub("", request.META.get("HTTP_X_CLIENT_ID", ""))[:40]
        request.request_id = request_id
        request.client_id = client_id

        started = time.monotonic()
        response = self.get_response(request)
        response["X-Request-ID"] = request_id

        # One line per traced API request. Only when the caller identifies
        # itself: webhooks, health checks and crawlers stay out of it.
        if client_id and request.path.startswith("/api/"):
            logger.info(
                "trace %s %s -> %s",
                request.method,
                request.path,
                response.status_code,
                extra={
                    "client_id": client_id,
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "duration_ms": round((time.monotonic() - started) * 1000, 1),
                },
            )
        return response
