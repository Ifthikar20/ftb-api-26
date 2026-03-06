import threading

_local = threading.local()


def get_correlation_id():
    return getattr(_local, "correlation_id", None)


class CorrelationMiddleware:
    """
    Sets correlation ID in thread-local storage for distributed tracing.
    Allows correlation ID to be accessed from anywhere in the request lifecycle.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.correlation_id = getattr(request, "request_id", None)
        response = self.get_response(request)
        _local.correlation_id = None
        return response
