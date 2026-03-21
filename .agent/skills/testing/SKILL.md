---
description: Testing patterns for the FetchBot project. Apply when writing or running tests for backend or frontend code.
---

# FetchBot Testing Patterns

## Backend Testing (pytest + Django)

### Running Tests

```bash
cd /Users/ifthikaraliseyed/Desktop/FTB_APP/ftb-api-26
source venv/bin/activate
python -m pytest apps/<app>/tests/ -v
```

Note: Requires PostgreSQL running locally with a `postgres` role. If the DB is not available, verify imports instead:

```bash
source venv/bin/activate
DJANGO_SETTINGS_MODULE=config.settings.test python -c "
import django; django.setup()
from apps.<app>.api.v1 import views, urls
print('Views:', [c for c in dir(views) if 'View' in c])
print('URLs:', len(urls.urlpatterns))
"
```

### Test Factories (factory_boy)

Each app has `tests/factories.py` with `DjangoModelFactory` subclasses:

```python
import factory
from factory.django import DjangoModelFactory
from apps.accounts.tests.factories import UserFactory

class MyModelFactory(DjangoModelFactory):
    class Meta:
        model = MyModel
    
    name = factory.Sequence(lambda n: f"Item {n}")
    website = factory.SubFactory(WebsiteFactory)
    user = factory.SubFactory(UserFactory)
```

Key factories to reuse:
- `apps.accounts.tests.factories.UserFactory` -- creates test users
- `apps.leads.tests.factories.WebsiteFactory` -- creates test websites (with WebsiteSettings)
- `apps.leads.tests.factories.VisitorFactory` -- creates test visitors
- `apps.leads.tests.factories.LeadFactory` -- creates test leads

### Test Structure

```python
import pytest
from rest_framework.test import APIClient
from apps.accounts.tests.factories import UserFactory

@pytest.fixture
def auth_client():
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user

@pytest.mark.django_db
class TestMyView:
    def test_authenticated_access(self, auth_client):
        client, user = auth_client
        response = client.get("/api/v1/my-endpoint/")
        assert response.status_code == 200
    
    def test_unauthenticated_rejected(self):
        client = APIClient()
        response = client.get("/api/v1/my-endpoint/")
        assert response.status_code == 401
    
    def test_wrong_user_returns_404(self):
        other = UserFactory()
        client = APIClient()
        client.force_authenticate(user=other)
        response = client.get("/api/v1/my-endpoint/")
        assert response.status_code == 404
```

### Test Checklist

For every new endpoint, write tests covering:
- [ ] Authenticated access returns 200/201
- [ ] Unauthenticated access returns 401
- [ ] Wrong user access returns 404 (ownership check)
- [ ] Valid data creates/updates correctly
- [ ] Invalid data returns 400
- [ ] Not-found resource returns 404

## Frontend Testing

### Vite Build Verification

```bash
cd /Users/ifthikaraliseyed/Desktop/FTB_APP/ftb-api-26/frontend
npx vite build
```

A clean build with no errors confirms all imports resolve and templates compile.

### Emoji Scan

After any UI changes, verify no emojis were introduced:

```bash
grep -nP '[\x{1F300}-\x{1F9FF}\x{2600}-\x{26FF}\x{2700}-\x{27BF}]' frontend/src/pages/*.vue frontend/src/components/*.vue
```

Expected output: no matches.
