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
            envelope = {
                "success": True,
                "data": data["results"],
                "meta": {
                    "count": data.get("count"),
                    "next": data.get("next"),
                    "previous": data.get("previous"),
                },
            }
        else:
            envelope = {"success": True, "data": data}

        return super().render(envelope, accepted_media_type, renderer_context)
