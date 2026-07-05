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
        build_time = settings.BUILD_TIME
        build_number = settings.BUILD_NUMBER

        # Human-readable marker shown in the login footer: vMMDD-N,
        # where MMDD is the UTC deploy date sliced from the ISO
        # BUILD_TIME and N is the commit count on main (BUILD_NUMBER),
        # which increases with every merge.
        if build_time and build_number:
            label = f"v{build_time[5:7]}{build_time[8:10]}-{build_number}"
        else:
            label = "dev"

        return Response(
            {
                "label": label,
                "version": sha[:7] if sha else "dev",
                "build": build_number or None,
                "built_at": build_time or None,
            }
        )
