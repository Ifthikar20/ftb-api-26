"""Public service API for the search_console app.

Note: `is_configured` exists in both gsc_client and oauth_service — import
it from the fully-qualified module path to avoid ambiguity.
"""
from apps.search_console.services.gsc_client import (
    list_sites,
    query_all_rows,
    query_search_analytics,
)
from apps.search_console.services.ingestion_service import (
    compute_sync_window,
    prune_old_rows,
    sync_window,
)
from apps.search_console.services.oauth_service import (
    auto_match_property,
    build_authorize_url,
    complete_connection,
    disconnect,
    exchange_code,
    parse_state,
    refresh_access_token,
)
from apps.search_console.services.prompt_feed import feed_prompts_for_website

__all__ = [
    "list_sites",
    "query_all_rows",
    "query_search_analytics",
    "compute_sync_window",
    "prune_old_rows",
    "sync_window",
    "auto_match_property",
    "build_authorize_url",
    "complete_connection",
    "disconnect",
    "exchange_code",
    "parse_state",
    "refresh_access_token",
    "feed_prompts_for_website",
]
