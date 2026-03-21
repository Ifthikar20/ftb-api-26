---
description: Django backend development patterns for FetchBot. Apply when creating or modifying backend apps, views, services, or models.
---

# FetchBot Backend Patterns

Follow these conventions when working on the FetchBot Django backend.

## Project Structure

Each Django app follows this structure:
```
apps/<app_name>/
  __init__.py
  admin.py
  apps.py
  models.py
  tasks.py              # Celery async tasks
  api/
    __init__.py
    v1/
      __init__.py
      urls.py
      views.py
      serializers.py
  services/
    __init__.py
    <feature>_service.py  # Business logic layer
  tests/
    __init__.py
    factories.py          # factory_boy test factories
    test_views.py
    test_services.py
  migrations/
```

## Existing Apps

| App | Purpose |
|-----|---------|
| `accounts` | User auth, JWT, OAuth |
| `analytics` | Pageviews, visitors, funnels, daily stats |
| `agents` | AI agent workflows |
| `audits` | SEO/performance/security site audits |
| `billing` | Stripe subscriptions |
| `competitors` | Competitor tracking |
| `leads` | Lead scoring, segments, AI finder, email outreach |
| `notifications` | Push/email notifications |
| `strategy` | AI growth strategy |
| `websites` | Website/project management |

## Views

- All views inherit from `rest_framework.views.APIView`
- Use `permission_classes = [IsAuthenticated]` for all protected endpoints
- Always call `WebsiteService.get_for_user(user=request.user, website_id=website_id)` to verify ownership
- Return data through DRF serializers
- Use `StandardPagination` from `core.interceptors.pagination` for list endpoints

Response format:
```python
# Standard response (auto-wrapped by DRF)
return Response(serializer.data)

# With status
return Response(data, status=status.HTTP_201_CREATED)

# Paginated
paginator = StandardPagination()
page = paginator.paginate_queryset(queryset, request)
serializer = MySerializer(page, many=True)
return paginator.get_paginated_response(serializer.data)
```

## Services

- Business logic lives in service classes, NOT in views
- Services are classes with `@staticmethod` methods
- Use keyword-only arguments: `def method(*, param1, param2)`
- Raise `ResourceNotFound` from `core.exceptions` for missing resources
- Use `audit_log()` from `core.logging.audit_logger` for important state changes

```python
from core.exceptions import ResourceNotFound
from core.logging.audit_logger import audit_log

class MyService:
    @staticmethod
    def get_item(*, website_id: str, item_id: str) -> Model:
        try:
            return Model.objects.get(id=item_id, website_id=website_id)
        except Model.DoesNotExist:
            raise ResourceNotFound("Item not found.")
```

## Models

- All models inherit from `TimestampMixin` (adds `created_at`, `updated_at`)
- Use `SoftDeleteMixin` where logical deletion is needed
- Use UUIDs for primary keys (auto via mixins)
- Always set explicit `db_table` in Meta
- Add database indexes for frequently filtered fields

```python
from core.mixins.timestamp_mixin import TimestampMixin
from core.mixins.soft_delete_mixin import SoftDeleteMixin

class MyModel(SoftDeleteMixin, TimestampMixin):
    website = models.ForeignKey("websites.Website", on_delete=models.CASCADE, related_name="items")
    class Meta:
        db_table = "app_mymodel"
        indexes = [models.Index(fields=["website", "field"])]
```

## URL Patterns

- All API URLs are versioned under `/api/v1/<app>/`
- Use `<uuid:param_id>` for UUID path params
- Name all URL patterns for reverse lookups

## Settings

- Environment variables loaded via `env()` in `config/settings/base.py`
- Settings files: `base.py` (shared), `dev.py` (local), `prod.py` (production), `test.py` (tests)
- External API keys: `ANTHROPIC_API_KEY`, `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID`, `SENDGRID_API_KEY`, etc.

## No Emojis

Never use emojis in backend code, logging, or responses. Use descriptive text instead.
