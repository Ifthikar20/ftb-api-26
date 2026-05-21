"""REST endpoints for the prompt library.

The API has two audiences:

* The onboarding flow + LLM Ranking dashboard, which need read-only
  access to industries and a paginated browse of prompts.
* The Run Audit modal, which previews and persists a per-audit
  prompt sample (a :class:`PromptSampleRun`).
"""
from __future__ import annotations

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
    TestEnvironment,
)
from apps.prompt_library.services.sampler_service import sample_prompts_for_audit
from apps.websites.services.website_service import WebsiteService
from core.interceptors.pagination import StandardPagination


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
        if data.get("industry_id"):
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

        template_text = data["template_text"].strip()
        body_for_text = data.get("text") or template_text
        variables = extract_variables(template_text)
        # Reuse a prompt with the same canonical text if it already exists,
        # otherwise create one. This keeps the Prompt table de-duped while
        # still letting every website link its own copy via BrandPrompt.
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
        # Link the prompt to the website so it shows in the Saved tab.
        # The Saved tab reads BrandPrompt rows, not Prompt rows directly.
        brand_prompt, _ = BrandPrompt.objects.get_or_create(
            website=website, prompt=prompt,
        )
        payload = PromptSerializer(prompt).data
        # FE needs the BrandPrompt id to chain into "add to env" calls.
        payload["brand_prompt_id"] = str(brand_prompt.id)
        return Response(payload, status=status.HTTP_201_CREATED)


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
