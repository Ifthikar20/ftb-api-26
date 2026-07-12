"""Public service API for the citations app."""
from apps.citations.services.content_reader import (
    read_page,
    read_reddit_thread,
    read_url,
    read_yelp,
)
from apps.citations.services.domain_classifier import classify, collect_competitor_apexes
from apps.citations.services.extraction_service import count_references, extract_for_result
from apps.citations.services.snapshot_service import (
    compute_audit_breakdown,
    compute_for_website,
    compute_global,
)
from apps.citations.services.source_scan import derive_opportunities, run_scan
from apps.citations.services.source_sentiment import analyze_content, assess_serp_relevance
from apps.citations.services.url_analytics import (
    build_chat_detail,
    build_url_detail,
    build_urls_overview,
    classify_url_type,
    domain_type_for,
    extract_response_brands,
    model_key,
    topic_of,
    tracked_competitors,
)
from apps.citations.services.url_normalizer import extract_apex_domain, normalize_url
from apps.citations.services.web_search import search_web, summarize_url_with_perplexity

__all__ = [
    "read_page",
    "read_reddit_thread",
    "read_url",
    "read_yelp",
    "classify",
    "collect_competitor_apexes",
    "count_references",
    "extract_for_result",
    "compute_audit_breakdown",
    "compute_for_website",
    "compute_global",
    "derive_opportunities",
    "run_scan",
    "analyze_content",
    "assess_serp_relevance",
    "build_chat_detail",
    "build_url_detail",
    "build_urls_overview",
    "classify_url_type",
    "domain_type_for",
    "extract_response_brands",
    "model_key",
    "topic_of",
    "tracked_competitors",
    "extract_apex_domain",
    "normalize_url",
    "search_web",
    "summarize_url_with_perplexity",
]
