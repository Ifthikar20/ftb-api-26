from rest_framework.renderers import JSONRenderer


class EnvelopeRenderer(JSONRenderer):
    """
    Wraps all successful responses in:
    {
        "success": true,
        "data": { ... },
        "meta": { "count": 100, "next": "...", "previous": "..." }  // If paginated
    }
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None

        if response and response.status_code >= 400:
            # Error responses already formatted by exception handler
            return super().render(data, accepted_media_type, renderer_context)

        # Check if data is already wrapped (pagination does this)
        if isinstance(data, dict) and "results" in data:
            meta = {
                "count": data.get("count"),
                "next": data.get("next"),
                "previous": data.get("previous"),
            }
            # Views may attach extra top-level keys to a paginated
            # response (e.g. the rag source list adds ``stats`` so the
            # UI gets badge counts in one round-trip). Carry them into
            # meta instead of silently dropping them.
            for key, value in data.items():
                if key not in ("results", "count", "next", "previous"):
                    meta[key] = value
            envelope = {
                "success": True,
                "data": data["results"],
                "meta": meta,
            }
        else:
            envelope = {"success": True, "data": data}

        return super().render(envelope, accepted_media_type, renderer_context)
