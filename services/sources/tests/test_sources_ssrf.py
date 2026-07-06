"""SSRF guard of the sources service's local url_safety/safe_http copies.

Mirrors the core/validators test coverage so drift between the copies
and the originals surfaces here.
"""

from unittest.mock import MagicMock, patch

import pytest

from services.sources import safe_http, url_safety


@pytest.mark.parametrize("url", [
    "http://169.254.169.254/latest/meta-data/",
    "http://localhost/",
    "http://127.0.0.1:8000/",
    "http://10.0.0.5/",
    "http://192.168.1.1/",
    "http://[::1]/",
])
def test_private_and_loopback_refused(url):
    with pytest.raises(url_safety.UnsafeURLError):
        url_safety.assert_url_safe(url)


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.com/x",
    "gopher://example.com/",
])
def test_non_http_schemes_refused(url):
    with pytest.raises(url_safety.UnsafeURLError):
        url_safety.assert_url_safe(url)


def test_error_is_plain_exception_not_django():
    # The service copy must not depend on Django's ValidationError.
    assert issubclass(url_safety.UnsafeURLError, Exception)
    assert "django" not in url_safety.UnsafeURLError.__mro__[1].__module__


def test_redirect_to_private_refused():
    redirect = MagicMock()
    redirect.status_code = 302
    redirect.headers = {"Location": "http://169.254.169.254/"}
    with patch.object(safe_http, "assert_url_safe",
                      side_effect=["https://ok.example.com/", url_safety.UnsafeURLError("private")]), \
         patch.object(safe_http, "_do_request", return_value=redirect):
        with pytest.raises(safe_http.FetchError, match="redirect refused"):
            safe_http.safe_get("https://ok.example.com/")


def test_read_page_refuses_metadata_endpoint():
    from services.sources import logic
    out = logic.read_page("http://169.254.169.254/latest/meta-data/")
    assert out["status"] == "error"
    assert "unsafe URL" in out["detail"]
