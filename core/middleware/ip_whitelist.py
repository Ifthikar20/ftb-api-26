from django.conf import settings
from django.http import HttpResponseForbidden


class IPWhitelistMiddleware:
    """
    SOC2: Restrict admin panel access to whitelisted IPs.
    Only applies to /admin/ paths.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            allowed_ips = getattr(settings, "ADMIN_ALLOWED_IPS", [])
            if allowed_ips:
                client_ip = self._get_client_ip(request)
                if client_ip not in allowed_ips:
                    return HttpResponseForbidden("Access denied.")
        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.META.get("REMOTE_ADDR")
