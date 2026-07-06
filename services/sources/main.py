"""
Sources service: web search (Perplexity) and content readers.

Internal-only FastAPI app. Reached from web/celery at
http://sources.ftb.internal:8000 on the compose network; never exposed
through nginx or public DNS. Auth is a static bearer token
(SOURCES_AUTH_TOKEN) shared with the Django callers via .env.prod.

Stateless: the per-user search quota and circuit breaker stay in the
Django facade (apps/citations/services/web_search.py). The SSRF guard
for /v1/read runs here via the local safe_http module.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.sources import logic

app = FastAPI(title="ftb-sources", docs_url=None, redoc_url=None)


def require_token(request: Request) -> None:
    expected = os.environ.get("SOURCES_AUTH_TOKEN", "")
    if not expected:
        # A missing token is a deployment error; refuse rather than fail open.
        raise HTTPException(status_code=503, detail="service token not configured")
    header = request.headers.get("Authorization", "")
    provided = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="invalid token")


class SearchBody(BaseModel):
    query: str
    max_results: int = logic.DEFAULT_MAX_RESULTS
    timeout: float = 20.0


class ReadBody(BaseModel):
    url: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/search", dependencies=[Depends(require_token)])
def search(body: SearchBody):
    api_key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not api_key:
        return JSONResponse(status_code=503, content={"error": "not_configured"})
    try:
        results = logic.perplexity_search(
            body.query,
            api_key=api_key,
            max_results=body.max_results,
            timeout=body.timeout,
        )
    except logic.SearchRequestError as exc:
        return JSONResponse(
            status_code=502,
            content={"error": "upstream_request_failed", "detail": str(exc)[:300]},
        )
    except logic.SearchParseError as exc:
        return JSONResponse(
            status_code=502,
            content={"error": "upstream_parse_failed", "detail": str(exc)[:300]},
        )
    return {"results": results}


@app.post("/v1/read", dependencies=[Depends(require_token)])
def read(body: ReadBody) -> dict:
    return logic.read_url(
        body.url,
        yelp_api_key=os.environ.get("YELP_API_KEY", ""),
    )
