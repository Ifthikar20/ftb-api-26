"""Public service API for the llm_ranking app.

Note: modules with colliding names (build_for_user, quota_for_user,
quota_remaining, is_configured, search) are not re-exported here — import
them from their fully-qualified module path to avoid ambiguity.
"""
from apps.llm_ranking.services.audit_context import suggest_audit_context
from apps.llm_ranking.services.audit_runner import apply_to_audit, gather_prompts
from apps.llm_ranking.services.business_story import (
    gather_and_ingest,
    gather_story,
    render_story,
)
from apps.llm_ranking.services.citation_geo import (
    aggregate_countries,
    attribute_country,
    merge_country_counts,
)
from apps.llm_ranking.services.competitor_discovery import discover_competitors
from apps.llm_ranking.services.competitor_normalize import canonical_name, display_name
from apps.llm_ranking.services.content_enricher import ContentEnricher
from apps.llm_ranking.services.domain_scanner import scan_domain
from apps.llm_ranking.services.eta_service import (
    estimate_audit_duration,
    format_eta,
    schedule_eta,
)
from apps.llm_ranking.services.extraction_service import HaikuExtractionService
from apps.llm_ranking.services.geo_rewrite import rewrite
from apps.llm_ranking.services.geo_stats import (
    build_breakdowns_for_user,
    build_kpis_for_user,
)
from apps.llm_ranking.services.geo_tagger import recommendations_for, tag_prompts
from apps.llm_ranking.services.impression import (
    best_method_for_domain,
    inject_citation_markers,
    position_adjusted_word_counts,
    projected_lift,
    relative_improvement,
    word_count_impression,
)
from apps.llm_ranking.services.plackett_luce import (
    fit_plackett_luce,
    rankings_from_results,
)
from apps.llm_ranking.services.prompt_library import (
    PromptLibrary,
    PromptPack,
    PromptTemplate,
    funnel_stage_for,
    list_available_packs,
    load_pack,
    match_industry_pack,
    rationale_for,
)
from apps.llm_ranking.services.ranking_service import (
    LLMRankingService,
    beta_binomial_mean,
    build_enriched_system_prompt,
    wilson_ci,
)
from apps.llm_ranking.services.regions import (
    Region,
    flavor_prompt,
    get_region,
    region_for_country,
    region_system_instruction,
    supported_countries,
)
from apps.llm_ranking.services.scan_dispatch import dispatch_scan
from apps.llm_ranking.services.source_prompt_resolver import resolve_source_prompt_id
from apps.llm_ranking.services.subjective_impression import score_citation
from apps.llm_ranking.services.visibility_series import (
    build_month12_for_website,
    build_overview_for_website,
)

__all__ = [
    "suggest_audit_context",
    "apply_to_audit",
    "gather_prompts",
    "gather_and_ingest",
    "gather_story",
    "render_story",
    "aggregate_countries",
    "attribute_country",
    "merge_country_counts",
    "discover_competitors",
    "canonical_name",
    "display_name",
    "ContentEnricher",
    "scan_domain",
    "estimate_audit_duration",
    "format_eta",
    "schedule_eta",
    "HaikuExtractionService",
    "rewrite",
    "build_breakdowns_for_user",
    "build_kpis_for_user",
    "recommendations_for",
    "tag_prompts",
    "best_method_for_domain",
    "inject_citation_markers",
    "position_adjusted_word_counts",
    "projected_lift",
    "relative_improvement",
    "word_count_impression",
    "fit_plackett_luce",
    "rankings_from_results",
    "PromptLibrary",
    "PromptPack",
    "PromptTemplate",
    "funnel_stage_for",
    "list_available_packs",
    "load_pack",
    "match_industry_pack",
    "rationale_for",
    "LLMRankingService",
    "beta_binomial_mean",
    "build_enriched_system_prompt",
    "wilson_ci",
    "Region",
    "flavor_prompt",
    "get_region",
    "region_for_country",
    "region_system_instruction",
    "supported_countries",
    "dispatch_scan",
    "resolve_source_prompt_id",
    "score_citation",
    "build_month12_for_website",
    "build_overview_for_website",
]
