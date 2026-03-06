#!/usr/bin/env python
"""
Kubernetes health check script.
Returns exit code 0 if healthy, 1 if not.
"""
import sys
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

import django
django.setup()

try:
    from django.db import connection
    connection.ensure_connection()

    from django.core.cache import cache
    cache.set("health_check", "ok", 30)
    assert cache.get("health_check") == "ok"

    print("Health check passed.")
    sys.exit(0)
except Exception as e:
    print(f"Health check failed: {e}", file=sys.stderr)
    sys.exit(1)
