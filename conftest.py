import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Use the test database configuration."""
    pass


@pytest.fixture(autouse=True)
def reset_cache():
    """Clear cache between tests."""
    from django.core.cache import cache
    yield
    cache.clear()
