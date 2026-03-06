import uuid


class RequestIDMiddleware:
    """
    Assigns a unique X-Request-ID to every request for end-to-end tracing.
    If the client sends one (from Vue.js Axios interceptor), we use it.
    Otherwise we generate one. Included in all log entries and responses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get("HTTP_X_REQUEST_ID", str(uuid.uuid4()))
        request.request_id = request_id

        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response
