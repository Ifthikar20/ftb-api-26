"""REST endpoints for the prompt library.

The API has two audiences:

* The onboarding flow + LLM Ranking dashboard, which need read-only
  access to industries and a paginated browse of prompts.
* The Run Audit modal, which previews and persists a per-audit
  prompt sample (a :class:`PromptSampleRun`).
"""
from __future__ import annotations

import logging
import random

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.llm_ranking.models import LLMRankingAudit
from apps.prompt_library.api.v1.serializers import (
    AutoTemplateRequestSerializer,
    BrandPromptSerializer,
    GenerateFromContextRequestSerializer,
    IndustrySerializer,
    PreviewSampleRequestSerializer,
    PromptCreateSerializer,
    PromptSampleRunSerializer,
    PromptSerializer,
    PromptVariableSetSerializer,
    SmokeTestRequestSerializer,
    SynthesizeRequestSerializer,
    TestEnvironmentSerializer,
    UseLibrarySampleRequestSerializer,
)
from apps.prompt_library.models import (
    BrandPrompt,
    Industry,
    Prompt,
    PromptSource,
    PromptVariableSet,
    RejectedBrandPrompt,
    TestEnvironment,
)
from apps.prompt_library.services.sampler_service import sample_prompts_for_audit
from apps.websites.services.website_service import WebsiteService
from core.interceptors.pagination import StandardPagination

logger = logging.getLogger("apps")


class IndustryListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IndustrySerializer
    pagination_class = None

    def get_queryset(self):
        return Industry.objects.filter(is_active=True).order_by("name")


class PromptListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PromptSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Prompt.objects.filter(is_active=True).select_related("industry")
        industry_slug = self.request.query_params.get("industry")
        if industry_slug:
            qs = qs.filter(industry__slug=industry_slug)
        intent = self.request.query_params.get("intent_bucket")
        if intent:
            qs = qs.filter(intent_bucket=intent)
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(text__icontains=search)
        return qs.order_by("-demand_score", "-created_at")


class PreviewSampleView(APIView):
    """Return a non-persisted sample for the Run Audit preview drawer."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PreviewSampleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        industry = get_object_or_404(Industry, id=data["industry_id"], is_active=True)
        n = data["n"]
        seed = random.randint(0, 2**31 - 1)
        rng = random.Random(seed)

        pool = list(
            Prompt.objects.filter(industry=industry, is_active=True).order_by(
                "-demand_score", "-created_at"
            )[: max(n * 4, 50)]
        )
        rng.shuffle(pool)
        chosen = pool[:n]
        return Response(
            {
                "industry": IndustrySerializer(industry).data,
                "seed": seed,
                "strategy": data["strategy"],
                "prompts": PromptSerializer(chosen, many=True).data,
            }
        )


def _resolve_audit(user, audit_id) -> LLMRankingAudit:
    """Fetch an audit and verify the user owns the underlying website."""
    audit = get_object_or_404(LLMRankingAudit, id=audit_id)
    WebsiteService.get_for_user(user=user, website_id=audit.website_id)
    return audit


class UseLibrarySampleView(APIView):
    """Persist a PromptSampleRun on a draft audit and flip prompt_source."""

    permission_classes = [IsAuthenticated]

    def post(self, request, audit_id):
        audit = _resolve_audit(request.user, audit_id)
        serializer = UseLibrarySampleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        industry = get_object_or_404(Industry, id=data["industry_id"], is_active=True)
        if audit.status not in (LLMRankingAudit.STATUS_PENDING,):
            return Response(
                {"error": "audit_not_draft", "detail": "Sample can only be set on a pending audit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sample_run = sample_prompts_for_audit(
            audit_run=audit,
            industry=industry,
            n=data["n"],
            strategy=data["strategy"],
            seed=data.get("seed"),
        )
        # Default to library when the user explicitly opts in.
        if audit.prompt_source == LLMRankingAudit.PROMPT_SOURCE_VAULT:
            audit.prompt_source = LLMRankingAudit.PROMPT_SOURCE_LIBRARY
            audit.save(update_fields=["prompt_source"])
        return Response(PromptSampleRunSerializer(sample_run).data)


class GetAuditSampleView(APIView):
    """Return the persisted sample with provenance for the audit detail page."""

    permission_classes = [IsAuthenticated]

    def get(self, request, audit_id):
        audit = _resolve_audit(request.user, audit_id)
        sample_run = getattr(audit, "prompt_sample_run", None)
        if sample_run is None:
            return Response({"sample_run": None})
        return Response({"sample_run": PromptSampleRunSerializer(sample_run).data})


class IndustryTrendView(APIView):
    """Return cached Google Trends data for an industry."""

    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        from apps.prompt_library.services.trends_service import get_trend_payload

        industry = get_object_or_404(Industry, slug=slug, is_active=True)
        return Response(get_trend_payload(industry))


class WebsiteBrandPromptsView(APIView):
    """List or add brand prompts for a website."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        qs = (
            BrandPrompt.objects.filter(website=website)
            .select_related("prompt", "prompt__industry")
            .order_by("-created_at")
        )
        return Response(BrandPromptSerializer(qs, many=True).data)

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        serializer = BrandPromptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt = get_object_or_404(
            Prompt, id=serializer.validated_data["prompt_id"], is_active=True
        )
        bp, created = BrandPrompt.objects.get_or_create(
            website=website,
            prompt=prompt,
            defaults={"notes": serializer.validated_data.get("notes", "")},
        )
        return Response(
            BrandPromptSerializer(bp).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class BrandPromptDetailView(APIView):
    """Delete a single brand prompt entry."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, brand_prompt_id):
        bp = get_object_or_404(BrandPrompt, id=brand_prompt_id)
        WebsiteService.get_for_user(user=request.user, website_id=bp.website_id)
        bp.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Phase 3: templated prompts, effectiveness, variables, smoke test ──

class RegionsListView(APIView):
    """GET — country options for the Add Prompt location picker."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.llm_ranking.services.regions import supported_countries
        return Response({"countries": supported_countries()})


class WebsitePromptCreateView(APIView):
    """Create a manual templated prompt for a website."""

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id):
        from apps.prompt_library.services._hash import text_hash
        from apps.prompt_library.services.template_parser import extract_variables

        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        serializer = PromptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        industry = None
        topic_name = (data.get("topic") or "").strip()
        if topic_name:
            # Topic == bundle. Resolve or create the matching Industry so the
            # prompt (and any citations it later produces) file under it.
            from django.utils.text import slugify
            slug = slugify(topic_name)[:64] or "topic"
            industry, _ = Industry.objects.get_or_create(
                slug=slug,
                defaults={"name": topic_name, "is_active": True},
            )
        elif data.get("industry_id"):
            industry = get_object_or_404(Industry, id=data["industry_id"], is_active=True)
        else:
            # Pick a sensible default — the website's industry name maps
            # back to an Industry slug if one matches, else any active one.
            slug_hint = (getattr(website, "industry", "") or "").lower().strip().replace(" ", "-")
            industry = (
                Industry.objects.filter(slug=slug_hint, is_active=True).first()
                or Industry.objects.filter(is_active=True).order_by("name").first()
            )
        if industry is None:
            return Response(
                {"error": "no_industry_available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tags = [t.strip() for t in (data.get("tags") or []) if t and t.strip()]
        location = (data.get("location") or "").strip()

        # Each non-empty line becomes a separate prompt (matches the modal's
        # "every line is a prompt" + bulk-upload behaviour). Template-only
        # payloads (no newlines) collapse to a single prompt as before.
        raw = (data.get("text") or "").strip()
        template_text_in = (data.get("template_text") or "").strip()
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if not lines:
            lines = [template_text_in] if template_text_in else []

        created_prompts = []
        brand_prompt_ids = []
        for line in lines:
            template_text = template_text_in or line
            body_for_text = line or template_text
            variables = extract_variables(template_text)
            canonical_hash = text_hash(template_text or body_for_text)
            prompt, _ = Prompt.objects.get_or_create(
                text_hash=canonical_hash,
                defaults=dict(
                    industry=industry,
                    text=body_for_text,
                    template_text=template_text,
                    template_variables=variables,
                    intent_bucket=data.get("intent_bucket") or "category",
                    style=data.get("style") or "question",
                    source=PromptSource.MANUAL,
                ),
            )
            brand_prompt, _ = BrandPrompt.objects.get_or_create(
                website=website, prompt=prompt,
            )
            changed = []
            if tags and brand_prompt.tags != tags:
                brand_prompt.tags = tags
                changed.append("tags")
            if location and brand_prompt.location != location:
                brand_prompt.location = location
                changed.append("location")
            if changed:
                brand_prompt.save(update_fields=[*changed, "updated_at"])
            created_prompts.append(prompt)
            brand_prompt_ids.append(str(brand_prompt.id))

        if not created_prompts:
            return Response({"error": "no_prompts"}, status=status.HTTP_400_BAD_REQUEST)

        # Auto-scan: run the new prompts through the ranking pipeline so they
        # start collecting mentions/citations. Best-effort — never blocks or
        # fails the create if the queue or provider keys are unavailable.
        scan_audit_id = self._trigger_scan(
            website, request.user, [p.text for p in created_prompts], location,
        )

        payload = PromptSerializer(created_prompts[0]).data
        payload["brand_prompt_id"] = brand_prompt_ids[0]
        payload["brand_prompt_ids"] = brand_prompt_ids
        payload["created_count"] = len(created_prompts)
        payload["scan_audit_id"] = scan_audit_id
        return Response(payload, status=status.HTTP_201_CREATED)

    @staticmethod
    def _trigger_scan(website, user, prompts, location):
        """Kick off an LLM ranking audit for freshly added prompts."""
        try:
            from django.conf import settings as dj_settings

            from apps.llm_ranking.models import LLMRankingAudit
            from apps.llm_ranking.providers import PROVIDERS as PROV_REGISTRY
            from apps.llm_ranking.services.regions import region_for_country
            from apps.llm_ranking.services.scan_dispatch import dispatch_scan

            selected = [
                k for k, prov in PROV_REGISTRY.items()
                if getattr(dj_settings, prov.api_key_setting, "")
            ] or ["claude"]
            audit = LLMRankingAudit.objects.create(
                website=website,
                created_by=user,
                business_name=website.business_name or website.name or "",
                business_description=getattr(website, "description", "") or "",
                industry=getattr(website, "industry", "") or "",
                location=location or "",
                region=region_for_country(location),
                prompts=list(prompts),
                providers_queried=selected,
            )
            dispatch_scan(str(audit.id))
            return str(audit.id)
        except Exception:  # pragma: no cover - scan is best-effort
            logger.exception("auto-scan dispatch failed")
            return None


class PromptPreviewView(APIView):
    """Return a filled template + missing variables for a (prompt, website)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, prompt_id):
        from apps.prompt_library.services.variable_resolver import resolve_for_website

        prompt = get_object_or_404(Prompt, id=prompt_id)
        website_id = request.query_params.get("website")
        website = None
        if website_id:
            website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        filled, missing = resolve_for_website(website, prompt)
        return Response({
            "prompt_id": str(prompt.id),
            "filled_text": filled,
            "missing_variables": missing,
            "template_variables": list(prompt.template_variables or []),
        })


class PromptEffectivenessView(APIView):
    """Return the cached effectiveness envelope for a prompt."""

    permission_classes = [IsAuthenticated]

    def get(self, request, prompt_id):
        prompt = get_object_or_404(Prompt, id=prompt_id)
        components = dict(prompt.effectiveness_components or {})
        stable = bool(components.pop("stable", prompt.runs_count >= 3))
        runs = int(components.pop("runs", prompt.runs_count or 0))
        return Response({
            "prompt_id": str(prompt.id),
            "overall": prompt.effectiveness_score,
            "components": components,
            "stable": stable,
            "runs": runs,
        })


class PromptAutoTemplateView(APIView):
    """Convert raw text to a {{ variable }} template via the synthesis provider."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.prompt_library.services.auto_template import auto_template

        serializer = AutoTemplateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        envelope = auto_template(serializer.validated_data["raw_text"])
        return Response(envelope)


class PromptSearchSourcesView(APIView):
    """Live Google search lookup so the UI can show 'where this question is
    being asked from' (top organic results, classified by source domain).

    Body: ``{"query": "the prompt text"}``
    Returns: ``{"provider": "serpapi" | "unconfigured", "query": str,
                "results": [{title, url, domain, snippet, source_class, position}]}``
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.prompt_library.services.search_sources import search_sources

        query = (request.data or {}).get("query") or ""
        query = str(query).strip()
        if len(query) < 5:
            return Response(
                {"detail": "Query too short."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(search_sources(query, limit=8))


class PromptSmokeTestView(APIView):
    """Run a single prompt against one provider and return quality signals.

    Rate-limited per user via the existing token bucket (the underlying
    provider already enforces a per-provider RPM cap, so this view adds
    a coarser per-user guard to keep one user from saturating the bucket).
    """

    permission_classes = [IsAuthenticated]
    _SMOKE_BUCKET_CAPACITY = 10
    _SMOKE_BUCKET_REFILL = 10 / 60.0  # 10 calls per minute, refilled smoothly.

    def post(self, request, prompt_id):
        from apps.prompt_library.services.smoke_test import smoke_test_prompt
        from core.resilience import TokenBucket

        bucket = TokenBucket(
            name=f"prompt_smoke:{request.user.id}",
            capacity=self._SMOKE_BUCKET_CAPACITY,
            refill_per_second=self._SMOKE_BUCKET_REFILL,
        )
        if not bucket.try_acquire():
            return Response(
                {"error": "rate_limited", "detail": "Try again in a few seconds."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        prompt = get_object_or_404(Prompt, id=prompt_id)
        serializer = SmokeTestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        website = WebsiteService.get_for_user(
            user=request.user, website_id=data["website_id"],
        )
        envelope = smoke_test_prompt(
            prompt, website, provider=data["provider"], user=request.user,
        )
        return Response(envelope)


class PromptSynthesizeView(APIView):
    """Bulk-generate prompt templates via the synthesis provider."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.llm_ranking.providers import get_synthesis_provider
        from apps.prompt_library.services._hash import text_hash
        from apps.prompt_library.services.auto_template import auto_template

        serializer = SynthesizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        industry = get_object_or_404(Industry, id=data["industry_id"], is_active=True)

        provider = get_synthesis_provider()
        if provider is None:
            return Response(
                {"error": "no_synthesis_provider"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        body = (
            f"Generate {data['count']} distinct {data['style']}-style prompts a real "
            f"user might ask an AI assistant in the '{industry.name}' industry. Use "
            f"snake_case {{{{ variables }}}} for any tenant-specific noun (brand, "
            f"location, product, persona). Return a JSON list of strings only."
        )
        try:
            result = provider.query(
                body, "Return JSON array of strings only.",
                user=request.user, website=None,
                audit_id="prompt_library_synthesize", role="synthesis",
            )
        except Exception as exc:
            return Response(
                {"error": "synthesis_failed", "detail": str(exc)[:200]},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if not getattr(result, "succeeded", False):
            return Response(
                {"error": "synthesis_failed", "detail": getattr(result, "error", "")},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        import json
        import re

        text = getattr(result, "text", "") or ""
        match = re.search(r"\[.*\]", text, re.DOTALL)
        items: list[str] = []
        if match:
            try:
                items = [str(x) for x in json.loads(match.group()) if isinstance(x, str | int | float)]
            except Exception:
                items = []
        created = []
        for raw in items[: data["count"]]:
            envelope = auto_template(raw)
            template_text = envelope["template_text"].strip()
            if not template_text:
                continue
            h = text_hash(template_text)
            if Prompt.objects.filter(industry=industry, text_hash=h).exists():
                continue
            prompt = Prompt.objects.create(
                industry=industry,
                text=raw.strip(),
                template_text=template_text,
                template_variables=envelope["template_variables"],
                style=envelope["style"] or data["style"],
                intent_bucket="category",
                source=PromptSource.LLM_SYNTH,
                text_hash=h,
            )
            created.append(prompt)
        return Response({
            "created": len(created),
            "prompts": PromptSerializer(created, many=True).data,
        })


class PromptGenerateFromContextView(APIView):
    """Generate ~20 templated prompts from a free-form context description.

    Calls the synthesis provider (DeepSeek when configured, Anthropic
    fallback). Optionally persists the generated prompts as ``Prompt`` rows
    on a website's industry. Throttled per-user via ``TokenBucket`` to
    keep one user from burning the API budget.
    """

    permission_classes = [IsAuthenticated]
    _BUCKET_CAPACITY = 6
    _BUCKET_REFILL = 6 / 60.0  # 6 calls per minute, smooth refill.

    def post(self, request):
        from apps.prompt_library.services._hash import text_hash
        from apps.prompt_library.services.context_generator import (
            generate_from_context,
        )
        from core.resilience import TokenBucket

        bucket = TokenBucket(
            name=f"prompt_ctx_gen:{request.user.id}",
            capacity=self._BUCKET_CAPACITY,
            refill_per_second=self._BUCKET_REFILL,
        )
        if not bucket.try_acquire():
            return Response(
                {"error": "rate_limited", "detail": "Too many generations. Wait a moment."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = GenerateFromContextRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        items, provider_name = generate_from_context(
            data["context"], count=data["count"], user=request.user,
        )

        persisted: list = []
        if data.get("persist") and data.get("website_id"):
            website = WebsiteService.get_for_user(
                user=request.user, website_id=data["website_id"],
            )
            slug_hint = (getattr(website, "industry", "") or "").lower().strip().replace(" ", "-")
            industry = (
                Industry.objects.filter(slug=slug_hint, is_active=True).first()
                or Industry.objects.filter(is_active=True).order_by("name").first()
            )
            if industry is not None:
                for item in items:
                    template_text = item["template_text"]
                    h = text_hash(template_text)
                    if Prompt.objects.filter(industry=industry, text_hash=h).exists():
                        continue
                    prompt = Prompt.objects.create(
                        industry=industry,
                        text=item.get("preview_text") or template_text,
                        template_text=template_text,
                        template_variables=item["template_variables"],
                        style=item["style"],
                        intent_bucket=item["intent_bucket"],
                        source=PromptSource.LLM_SYNTH,
                        text_hash=h,
                    )
                    persisted.append(prompt)

        return Response({
            "generated": items,
            "provider": provider_name,
            "persisted": PromptSerializer(persisted, many=True).data,
        })


class WebsiteVariablesView(APIView):
    """Get or replace the per-website prompt variable dictionary."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        from apps.prompt_library.services.variable_resolver import (
            variables_with_provenance,
        )

        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        var_set, _ = PromptVariableSet.objects.get_or_create(website=website)
        return Response({
            "variables": var_set.variables or {},
            "rows": variables_with_provenance(website),
        })

    def put(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        payload = request.data.get("variables")
        if not isinstance(payload, dict):
            return Response(
                {"error": "variables_must_be_object"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Coerce all values to strings — JSON-serialisable dicts of
        # str->str are the contract the template parser expects.
        cleaned = {str(k): ("" if v is None else str(v)) for k, v in payload.items() if k}
        var_set, _ = PromptVariableSet.objects.get_or_create(website=website)
        var_set.variables = cleaned
        var_set.save(update_fields=["variables", "updated_at"])
        return Response(PromptVariableSetSerializer(var_set).data)


class PromptToggleView(APIView):
    """Activate or deactivate a prompt (`/enable/` or `/disable/`)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, prompt_id, action: str):
        prompt = get_object_or_404(Prompt, id=prompt_id)
        if action == "enable":
            prompt.is_active = True
        elif action == "disable":
            prompt.is_active = False
        else:
            return Response({"error": "unknown_action"}, status=400)
        prompt.save(update_fields=["is_active", "updated_at"])
        return Response(PromptSerializer(prompt).data)


# ── Test Environments ─────────────────────────────────────────────
# An env is a named bucket of BrandPrompts on a Website. Created from
# either the Saved view ("Add selected to env") or the Model Test page
# ("Save current selection as env"). Lives in the same persistence so
# both surfaces see the same data.


class _EnvViewMixin:
    """Shared helpers — load env scoped to a website the user owns."""

    permission_classes = [IsAuthenticated]

    def _get_env(self, request, website_id, env_id) -> TestEnvironment:
        website = WebsiteService.get_for_user(
            user=request.user, website_id=website_id,
        )
        return get_object_or_404(
            TestEnvironment, id=env_id, website=website,
        )


class TestEnvironmentListView(APIView):
    """GET (list) and POST (create) for envs on a single website."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(
            user=request.user, website_id=website_id,
        )
        qs = (
            TestEnvironment.objects.filter(website=website)
            .prefetch_related("prompts")
            .order_by("-created_at")
        )
        return Response(TestEnvironmentSerializer(qs, many=True).data)

    def post(self, request, website_id):
        website = WebsiteService.get_for_user(
            user=request.user, website_id=website_id,
        )
        serializer = TestEnvironmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"]
        if TestEnvironment.objects.filter(website=website, name=name).exists():
            return Response(
                {"error": f"An environment named '{name}' already exists."},
                status=status.HTTP_409_CONFLICT,
            )
        env = TestEnvironment.objects.create(
            website=website, name=name, created_by=request.user,
        )
        # Optional initial prompt ids — saves the FE a second POST.
        prompt_ids = request.data.get("prompt_ids") or []
        if isinstance(prompt_ids, list) and prompt_ids:
            bps = BrandPrompt.objects.filter(
                website=website, id__in=prompt_ids,
            )
            env.prompts.add(*bps)
        return Response(
            TestEnvironmentSerializer(env).data,
            status=status.HTTP_201_CREATED,
        )


class TestEnvironmentDetailView(_EnvViewMixin, APIView):
    """GET (detail), PATCH (rename), DELETE for a single env."""

    def get(self, request, website_id, env_id):
        env = self._get_env(request, website_id, env_id)
        return Response(TestEnvironmentSerializer(env).data)

    def patch(self, request, website_id, env_id):
        env = self._get_env(request, website_id, env_id)
        new_name = (request.data.get("name") or "").strip()
        if not new_name:
            return Response({"error": "Name is required."},
                            status=status.HTTP_400_BAD_REQUEST)
        if (TestEnvironment.objects
                .filter(website=env.website, name=new_name)
                .exclude(id=env.id).exists()):
            return Response(
                {"error": f"An environment named '{new_name}' already exists."},
                status=status.HTTP_409_CONFLICT,
            )
        env.name = new_name
        env.save(update_fields=["name", "updated_at"])
        return Response(TestEnvironmentSerializer(env).data)

    def delete(self, request, website_id, env_id):
        env = self._get_env(request, website_id, env_id)
        env.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TestEnvironmentPromptsView(_EnvViewMixin, APIView):
    """Add/remove BrandPrompt rows from an env's prompt set.

    POST   /<env_id>/prompts/  { brand_prompt_ids: [..] }
    DELETE /<env_id>/prompts/  { brand_prompt_ids: [..] }
    """

    def post(self, request, website_id, env_id):
        env = self._get_env(request, website_id, env_id)
        ids = request.data.get("brand_prompt_ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"error": "brand_prompt_ids must be a non-empty list."},
                            status=status.HTTP_400_BAD_REQUEST)
        # Scope the lookup to this website so a malicious caller can't
        # graft prompts from another tenant into this env.
        bps = BrandPrompt.objects.filter(website=env.website, id__in=ids)
        env.prompts.add(*bps)
        return Response(TestEnvironmentSerializer(env).data)

    def delete(self, request, website_id, env_id):
        env = self._get_env(request, website_id, env_id)
        ids = request.data.get("brand_prompt_ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"error": "brand_prompt_ids must be a non-empty list."},
                            status=status.HTTP_400_BAD_REQUEST)
        bps = BrandPrompt.objects.filter(website=env.website, id__in=ids)
        env.prompts.remove(*bps)
        return Response(TestEnvironmentSerializer(env).data)


class BrandPromptDetailAggView(APIView):
    """
    Per-prompt analytics drilldown — what every model said about the
    brand when asked this exact prompt, aggregated across every audit
    that has run it on this website.

    Returns:
      - prompt: text, intent, topic, demand_score, runs_count
      - status: "active" / "inactive" based on Prompt.is_active and
        whether the brand currently has it via BrandPrompt
      - per-brand visibility, sov, sentiment, position
      - top domains cited in matching responses with citation rates
      - domain type breakdown
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _normalise(text: str) -> str:
        return " ".join((text or "").split()).lower()

    def get(self, request, website_id, prompt_id):
        from collections import Counter, defaultdict

        from django.db.models import Q

        from apps.citations.models import Citation
        from apps.llm_ranking.models import LLMRankingResult

        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)

        try:
            prompt = Prompt.objects.select_related("industry").get(id=prompt_id)
        except Prompt.DoesNotExist:
            return Response({"detail": "Prompt not found."},
                            status=status.HTTP_404_NOT_FOUND)

        bp = BrandPrompt.objects.filter(website=website, prompt=prompt).first()
        bp_exists = bp is not None
        bp_location = bp.location if bp else ""
        bp_tags = bp.tags if bp else []

        # Match every LLMRankingResult on this website whose prompt text
        # equals the prompt's text OR template_text. The audit serializer
        # stores the resolved text on the result, so we compare against
        # both shapes to catch templated variants.
        norm_text = self._normalise(prompt.text)
        norm_template = self._normalise(prompt.template_text or "")
        candidates = (
            LLMRankingResult.objects
            .filter(audit__website=website)
            .filter(Q(prompt__icontains=prompt.text[:80]) | Q(prompt__icontains=(prompt.template_text or "")[:80]))
            .only(
                "id", "provider", "prompt", "response_text",
                "is_mentioned", "mention_rank", "sentiment",
                "competitors_mentioned", "created_at",
                "citation_countries", "query_succeeded",
            )
        )

        results = []
        for r in candidates:
            rn = self._normalise(r.prompt)
            if rn == norm_text or (norm_template and rn == norm_template):
                results.append(r)

        total_results = len(results)

        # ── Per-brand visibility / SOV / sentiment / position ──────────
        brand_label = website.business_name or website.name or "your brand"
        brand_label_lower = brand_label.lower()

        brand_stats: dict[str, dict] = {}

        def _ensure(name: str) -> dict:
            key = name.strip().lower()
            if not key:
                return {}
            row = brand_stats.get(key)
            if row is None:
                row = {
                    "key": key,
                    "name": name.strip(),
                    "mentions": 0,
                    "responses_with_mention": 0,
                    "sentiments": [],
                    "positions": [],
                }
                brand_stats[key] = row
            return row

        for r in results:
            if r.is_mentioned:
                row = _ensure(brand_label)
                row["responses_with_mention"] += 1
                row["mentions"] += 1
                if r.mention_rank is not None:
                    row["positions"].append(r.mention_rank)
                if r.sentiment and r.sentiment != "not_mentioned":
                    row["sentiments"].append(r.sentiment)
            for comp in (r.competitors_mentioned or []):
                name = (comp.get("name") if isinstance(comp, dict) else None) or ""
                if not name:
                    continue
                if name.strip().lower() == brand_label_lower:
                    continue
                row = _ensure(name)
                row["responses_with_mention"] += 1
                row["mentions"] += 1

        total_mentions = sum(row["mentions"] for row in brand_stats.values()) or 1
        brands_out = []
        for row in brand_stats.values():
            avg_pos = round(sum(row["positions"]) / len(row["positions"]), 1) if row["positions"] else None
            # Map sentiment strings to a 0..100 scale for the display:
            # positive=85, neutral=55, negative=25. Averages produce a
            # rough indicator the UI shows as a small "•" pill value.
            smap = {"positive": 85, "neutral": 55, "negative": 25}
            scores = [smap.get(s, 50) for s in row["sentiments"]]
            sentiment_score = round(sum(scores) / len(scores), 1) if scores else None
            vis_pct = round(100 * row["responses_with_mention"] / total_results, 1) if total_results else 0.0
            sov_pct = round(100 * row["mentions"] / total_mentions, 1)
            brands_out.append({
                "name": row["name"],
                "is_self": row["key"] == brand_label_lower,
                "visibility_pct": vis_pct,
                "sov_pct": sov_pct,
                "sentiment_score": sentiment_score,
                "avg_position": avg_pos,
                "mentions": row["mentions"],
            })
        brands_out.sort(key=lambda x: (-x["visibility_pct"], -x["mentions"]))

        # ── Top domains + type breakdown from citations on these results
        result_ids = [r.id for r in results]
        citations_qs = Citation.objects.filter(result_id__in=result_ids).only(
            "apex_domain", "domain", "source_class", "result_id",
        )
        per_domain: dict[str, dict] = {}
        responses_with_citation: dict[str, set] = defaultdict(set)
        sources_by_result: dict[str, list] = defaultdict(list)
        for c in citations_qs:
            apex = c.apex_domain or c.domain
            if not apex:
                continue
            entry = per_domain.setdefault(apex, {
                "domain": c.domain,
                "apex_domain": apex,
                "source_class": c.source_class,
                "count": 0,
            })
            entry["count"] += 1
            responses_with_citation[apex].add(c.result_id)
            sources_by_result[c.result_id].append(apex)

        top_domains = []
        for apex, entry in per_domain.items():
            unique_responses = len(responses_with_citation[apex])
            entry["citation_rate"] = (
                round(unique_responses / total_results, 2) if total_results else 0.0
            )
            entry["retrieved_pct"] = (
                round(100 * unique_responses / total_results, 1) if total_results else 0.0
            )
            top_domains.append(entry)
        top_domains.sort(key=lambda e: (-e["count"], e["apex_domain"]))
        top_domains = top_domains[:25]

        type_counter: Counter = Counter()
        for entry in per_domain.values():
            type_counter[entry["source_class"] or "other"] += entry["count"]
        total_citations = sum(type_counter.values()) or 1
        type_breakdown = [
            {"key": key, "count": cnt, "pct": round(100 * cnt / total_citations, 1)}
            for key, cnt in type_counter.most_common()
        ]

        # ── Recent chats (one row per matching result, newest first) ──
        from apps.citations.services.url_analytics import model_key

        ordered = sorted(
            results, key=lambda r: r.created_at or prompt.created_at, reverse=True,
        )[:100]
        recent_chats = []
        for r in ordered:
            srcs, seen = [], set()
            for d in sources_by_result.get(r.id, []):
                if d and d not in seen:
                    seen.add(d)
                    srcs.append(d)
            cc = r.citation_countries or {}
            country = max(cc.items(), key=lambda kv: kv[1])[0] if isinstance(cc, dict) and cc else None
            has_response = bool((r.response_text or "").strip())
            recent_chats.append({
                "result_id": str(r.id),
                "prompt": r.prompt,
                "response_preview": (r.response_text or "")[:200],
                "brand_mentioned": r.is_mentioned,
                "position": r.mention_rank,
                "models": [model_key(r.provider)],
                "sources": srcs[:6],
                "country": country,
                "status": "complete" if has_response else "pending",
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })

        return Response({
            "prompt": {
                "id": str(prompt.id),
                "text": prompt.text,
                "template_text": prompt.template_text or "",
                "intent_bucket": prompt.intent_bucket,
                "topic": prompt.industry.name if prompt.industry_id else "",
                "location": bp_location,
                "tags": bp_tags,
                "demand_score": prompt.demand_score,
                "runs_count": prompt.runs_count,
                "effectiveness_score": prompt.effectiveness_score,
                "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
            },
            "is_brand_prompt": bp_exists,
            "status": "active" if (prompt.is_active and bp_exists) else "inactive",
            "total_responses": total_results,
            "brand_label": brand_label,
            "brands": brands_out,
            "top_domains": top_domains,
            "domain_types": type_breakdown,
            "total_retrievals": sum(type_counter.values()),
            "recent_chats": recent_chats,
        })


class WebsiteSavedPromptsAggView(APIView):
    """
    Saved-prompts dashboard payload — every saved prompt for the
    website plus aggregated metrics ready for the Saved tab table
    (visibility %, sentiment, position, models that mentioned, runs
    count, intent/style tags, volume bucket, topic).

    Heavier than the brand-prompts list endpoint but materialised in a
    single query pass plus a per-prompt response scan. Topics are
    derived from each prompt's industry name; intent + style are
    surfaced as tag chips.
    """

    permission_classes = [IsAuthenticated]

    # Number of library prompts we auto-attach to a brand-new website
    # the first time someone opens the Prompts dashboard. Keeps the
    # page from looking empty on a fresh signup.
    AUTOSEED_LIMIT = 12

    def _maybe_autoseed(self, website):
        """If this website has no BrandPrompts yet, copy the top library
        prompts in its industry over so the page lands populated.
        Idempotent — runs only when the count is exactly zero."""
        if BrandPrompt.objects.filter(website=website).exists():
            return

        industry_slug = (website.industry or "").strip().lower()
        candidates = Prompt.objects.filter(is_active=True)
        industry = None
        if industry_slug:
            industry = (
                Industry.objects
                .filter(is_active=True)
                .filter(slug__iexact=industry_slug)
                .first()
                or Industry.objects
                .filter(is_active=True, name__iexact=website.industry)
                .first()
            )
        if industry is not None:
            candidates = candidates.filter(industry=industry)
        else:
            # No industry match — fall back to top-demand prompts across
            # the library so we still seed something useful.
            candidates = candidates.select_related("industry")

        seed = list(candidates.order_by("-demand_score", "-created_at")[: self.AUTOSEED_LIMIT])
        if not seed:
            return
        BrandPrompt.objects.bulk_create(
            [BrandPrompt(website=website, prompt=p) for p in seed],
            ignore_conflicts=True,
        )

    def get(self, request, website_id):
        from collections import Counter, defaultdict

        from apps.llm_ranking.models import LLMRankingResult

        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        self._maybe_autoseed(website)

        bps = (
            BrandPrompt.objects
            .filter(website=website)
            .select_related("prompt", "prompt__industry")
            .order_by("-created_at")
        )
        prompts_by_norm: dict[str, list] = defaultdict(list)
        rows = []
        for bp in bps:
            p = bp.prompt
            norm = " ".join((p.text or "").split()).lower()
            prompts_by_norm[norm].append(bp.id)
            rows.append({
                "_norm": norm,
                "id": str(p.id),
                "brand_prompt_id": str(bp.id),
                "text": p.text,
                "template_text": p.template_text or "",
                "topic": p.industry.name if p.industry_id else "",
                "topic_slug": p.industry.slug if p.industry_id else "",
                "intent_bucket": p.intent_bucket,
                "style": p.style,
                "tags": bp.tags or [],
                "location": bp.location or "",
                "demand_score": p.demand_score,
                "runs_count": p.runs_count,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "visibility_pct": 0,
                "sentiment_score": None,
                "avg_position": None,
                "models_mentioned": [],
                "total_mentions": 0,
                "responses_seen": 0,
            })

        # Pull every LLMRankingResult for this website's audits once.
        # Then bucket per normalised prompt text — fast even with
        # thousands of results because we hold them in memory.
        all_results = list(
            LLMRankingResult.objects
            .filter(audit__website=website)
            .only(
                "provider", "prompt", "is_mentioned", "mention_rank",
                "sentiment",
            ),
        )

        smap = {"positive": 85, "neutral": 55, "negative": 25}
        agg: dict[str, dict] = {}
        for r in all_results:
            key = " ".join((r.prompt or "").split()).lower()
            if key not in prompts_by_norm:
                continue
            entry = agg.setdefault(key, {
                "responses": 0,
                "mentioned": 0,
                "positions": [],
                "sentiments": [],
                "providers_mentioned": set(),
            })
            entry["responses"] += 1
            if r.is_mentioned:
                entry["mentioned"] += 1
                if r.mention_rank is not None:
                    entry["positions"].append(r.mention_rank)
                if r.sentiment and r.sentiment != "not_mentioned":
                    entry["sentiments"].append(r.sentiment)
                if r.provider:
                    entry["providers_mentioned"].add(r.provider)

        for row in rows:
            stats = agg.get(row["_norm"])
            if not stats:
                continue
            responses = stats["responses"]
            if responses:
                row["responses_seen"] = responses
                row["visibility_pct"] = round(100 * stats["mentioned"] / responses, 0)
            row["total_mentions"] = stats["mentioned"]
            if stats["positions"]:
                row["avg_position"] = round(sum(stats["positions"]) / len(stats["positions"]), 1)
            if stats["sentiments"]:
                scores = [smap.get(s, 50) for s in stats["sentiments"]]
                row["sentiment_score"] = round(sum(scores) / len(scores), 0)
            row["models_mentioned"] = sorted(stats["providers_mentioned"])

        # Drop the helper key before responding.
        for row in rows:
            row.pop("_norm", None)

        # Tag summary (over the full set, so the filter list is stable) and
        # optional ?tag= filter applied to the rows.
        tag_counter: Counter = Counter()
        for row in rows:
            for t in (row.get("tags") or []):
                tag_counter[t] += 1
        all_tags = [
            {"name": name, "count": count}
            for name, count in tag_counter.most_common()
        ]
        tag_filter = (request.query_params.get("tag") or "").strip()
        if tag_filter:
            rows = [r for r in rows if tag_filter in (r.get("tags") or [])]

        # Topic summary for the left rail.
        topic_counter: Counter = Counter()
        for row in rows:
            t = row.get("topic") or ""
            if t:
                topic_counter[t] += 1
        topics = [
            {"name": name, "count": count}
            for name, count in topic_counter.most_common()
        ]

        # Aggregate KPI for the strip above the table.
        with_vis = [r for r in rows if r["responses_seen"]]
        avg_vis = round(sum(r["visibility_pct"] for r in with_vis) / len(with_vis), 0) if with_vis else 0
        with_sent = [r for r in rows if r["sentiment_score"] is not None]
        avg_sent = round(sum(r["sentiment_score"] for r in with_sent) / len(with_sent), 0) if with_sent else None
        with_pos = [r for r in rows if r["avg_position"] is not None]
        avg_pos = round(sum(r["avg_position"] for r in with_pos) / len(with_pos), 1) if with_pos else None

        return Response({
            "website_id": str(website.id),
            "rows": rows,
            "total": len(rows),
            "topics": topics,
            "all_tags": all_tags,
            "kpi": {
                "visibility_pct": avg_vis,
                "sentiment_score": avg_sent,
                "avg_position": avg_pos,
            },
        })


class WebsiteSuggestedPromptsView(APIView):
    """
    Suggested-prompts view for the Prompt-library dashboard's
    'Suggested' subtab.

    Returns library prompts that:
      - Are active
      - Match the website's industry (when we can resolve it)
      - Are NOT already saved as BrandPrompts on this website
      - Have NOT been explicitly rejected via the × button

    Each row carries the same shape the saved-aggregate endpoint
    returns minus the per-prompt response metrics — visibility /
    sentiment / position aren't computed because suggestions haven't
    been audited yet.
    """

    permission_classes = [IsAuthenticated]
    LIMIT = 25

    def _resolve_industry(self, website):
        slug = (website.industry or "").strip().lower()
        if not slug:
            return None
        return (
            Industry.objects.filter(is_active=True, slug__iexact=slug).first()
            or Industry.objects.filter(is_active=True, name__iexact=website.industry).first()
        )

    def get(self, request, website_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)

        saved_ids = BrandPrompt.objects.filter(website=website).values_list("prompt_id", flat=True)
        rejected_ids = RejectedBrandPrompt.objects.filter(website=website).values_list("prompt_id", flat=True)

        qs = Prompt.objects.filter(is_active=True).exclude(id__in=list(saved_ids)).exclude(id__in=list(rejected_ids))
        industry = self._resolve_industry(website)
        if industry is not None:
            qs = qs.filter(industry=industry)

        suggestions = list(
            qs.select_related("industry")
            .order_by("-demand_score", "-created_at")[: self.LIMIT]
        )

        rows = []
        for p in suggestions:
            rows.append({
                "id": str(p.id),
                "text": p.text,
                "template_text": p.template_text or "",
                "topic": p.industry.name if p.industry_id else "",
                "intent_bucket": p.intent_bucket,
                "style": p.style,
                "demand_score": p.demand_score,
                "suggested_at": p.created_at.isoformat() if p.created_at else None,
            })

        # Topics summary for the rail's 'Suggested Topics' section —
        # only include topics that actually have suggestions waiting.
        topic_counts = (
            qs.values_list("industry__name", flat=True)
        )
        from collections import Counter
        counter = Counter(t for t in topic_counts if t)
        topics = [{"name": n, "count": c} for n, c in counter.most_common()]

        return Response({
            "website_id": str(website.id),
            "rows": rows,
            "topics": topics,
            "total": len(rows),
        })


class WebsiteSuggestionActionView(APIView):
    """
    Accept or reject a single suggested prompt.

    POST .../accept/{prompt_id}/  → creates a BrandPrompt row
    POST .../reject/{prompt_id}/  → creates a RejectedBrandPrompt row
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, prompt_id, action):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            prompt = Prompt.objects.get(id=prompt_id, is_active=True)
        except Prompt.DoesNotExist:
            return Response({"detail": "Prompt not found."},
                            status=status.HTTP_404_NOT_FOUND)
        if action == "accept":
            bp, _ = BrandPrompt.objects.get_or_create(website=website, prompt=prompt)
            # If the user had previously rejected this one, lift the
            # rejection so it doesn't keep being filtered out elsewhere.
            RejectedBrandPrompt.objects.filter(website=website, prompt=prompt).delete()
            return Response({"saved": True, "brand_prompt_id": str(bp.id)})
        if action == "reject":
            RejectedBrandPrompt.objects.get_or_create(website=website, prompt=prompt)
            return Response({"rejected": True})
        return Response({"detail": "action must be 'accept' or 'reject'."},
                        status=status.HTTP_400_BAD_REQUEST)


class WebsiteSuggestionBulkView(APIView):
    """Accept or reject every prompt id passed in the body in one shot."""

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, action):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        ids = request.data.get("prompt_ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "prompt_ids must be a non-empty array."},
                            status=status.HTTP_400_BAD_REQUEST)
        if action not in ("accept", "reject"):
            return Response({"detail": "action must be 'accept' or 'reject'."},
                            status=status.HTTP_400_BAD_REQUEST)

        prompts = list(Prompt.objects.filter(is_active=True, id__in=ids))
        if action == "accept":
            BrandPrompt.objects.bulk_create(
                [BrandPrompt(website=website, prompt=p) for p in prompts],
                ignore_conflicts=True,
            )
            RejectedBrandPrompt.objects.filter(website=website, prompt__in=prompts).delete()
            return Response({"accepted": len(prompts)})

        RejectedBrandPrompt.objects.bulk_create(
            [RejectedBrandPrompt(website=website, prompt=p) for p in prompts],
            ignore_conflicts=True,
        )
        return Response({"rejected": len(prompts)})


class PromptFanoutsView(APIView):
    """List fan-out sub-queries the crawler captured for a saved prompt."""

    permission_classes = [IsAuthenticated]

    def get(self, request, website_id, prompt_id):
        from apps.prompt_library.models import PromptCrawlRun, PromptFanout

        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            prompt = Prompt.objects.get(id=prompt_id)
        except Prompt.DoesNotExist:
            return Response({"detail": "Prompt not found."},
                            status=status.HTTP_404_NOT_FOUND)

        fanouts = list(
            PromptFanout.objects
            .filter(website=website, prompt=prompt)
            .values("id", "text", "provider", "source", "confidence", "created_at")
            .order_by("-created_at")[:50]
        )
        last_run = (
            PromptCrawlRun.objects
            .filter(website=website, prompt=prompt)
            .order_by("-created_at")
            .first()
        )

        return Response({
            "website_id": str(website.id),
            "prompt_id": str(prompt.id),
            "fanouts": [
                {**f, "id": str(f["id"]),
                 "created_at": f["created_at"].isoformat() if f["created_at"] else None}
                for f in fanouts
            ],
            "last_run": {
                "id": str(last_run.id),
                "status": last_run.status,
                "fanout_count": last_run.fanout_count,
                "source_count": last_run.source_count,
                "providers": last_run.providers,
                "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
                "completed_at": last_run.completed_at.isoformat() if last_run.completed_at else None,
                "error": last_run.error or "",
            } if last_run else None,
        })


class PromptCrawlTriggerView(APIView):
    """Kick off a Celery task to crawl this prompt across providers."""

    permission_classes = [IsAuthenticated]

    def post(self, request, website_id, prompt_id):
        website = WebsiteService.get_for_user(user=request.user, website_id=website_id)
        try:
            prompt = Prompt.objects.get(id=prompt_id)
        except Prompt.DoesNotExist:
            return Response({"detail": "Prompt not found."},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            from apps.prompt_library.tasks import crawl_prompt_for_website
            crawl_prompt_for_website.delay(str(website.id), str(prompt.id))
            queued = True
        except Exception:
            # Celery worker not running — fall back to sync so the
            # button still does something useful in dev.
            from apps.prompt_library.services.prompt_crawler import crawl_prompt
            crawl_prompt(website, prompt)
            queued = False
        return Response({"queued": queued, "website_id": str(website.id),
                         "prompt_id": str(prompt.id)})
