"""Unauthenticated build-identity endpoint.

Reports which backend build is running so we can tell at a glance what
code a deployment is serving. The values come from Docker build args
injected by scripts/deploy.sh (GIT_SHA, BUILD_NUMBER, BUILD_TIME); in
local dev they are empty and the endpoint reports "dev".

Intentionally exposes only the short commit hash and a commit count.
Neither is sensitive: they identify a build without revealing code.
"""

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class VersionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        sha = settings.GIT_SHA
        return Response(
            {
                "version": sha[:7] if sha else "dev",
                "build": settings.BUILD_NUMBER or None,
                "built_at": settings.BUILD_TIME or None,
            }
        )
