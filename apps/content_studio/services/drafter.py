"""Drafter — generate a :class:`ContentDraft` for a :class:`ContentBrief`.

Steps:
1. Build a system prompt using the website's top tone samples.
2. Build a user prompt with the brief's structure, target keywords,
   grounded brand facts, and format-specific output constraints.
3. Call Anthropic if an API key is configured; otherwise emit a
   deterministic stub draft so tests can run without network.
4. Persist the draft and run the voice + accuracy guards.
"""
from __future__ import annotations

import json
import logging
import re

from django.conf import settings

from apps.brand_vault.models import ToneSample
from apps.content_studio.models import (
    BriefStatus,
    ContentBrief,
    ContentDraft,
    ContentFormat,
    DraftStatus,
)
from apps.content_studio.services import accuracy_guard, voice_guard
from core.llm import ClaudeUtility

logger = logging.getLogger("apps")


def _tone_summary(website) -> str:
    samples = list(ToneSample.objects.filter(website=website).order_by("-created_at")[:5])
    if not samples:
        return "Default professional, helpful brand voice."
    lines = []
    for s in samples:
        snippet = (s.text or "").strip().replace("\n", " ")
        if snippet:
            lines.append(f"- {snippet[:240]}")
    return "Use a tone consistent with these samples:\n" + "\n".join(lines)


def _facts_block(brief: ContentBrief) -> str:
    facts = list(brief.grounded_facts.all()[:10])
    if not facts:
        return "No grounded facts; rely on the brief description only."
    return "Approved brand facts to ground the draft:\n" + "\n".join(
        f"- {f.subject} {f.predicate} {f.object}" for f in facts
    )


def _format_instructions(fmt: str) -> str:
    if fmt == ContentFormat.FAQ.value:
        return (
            "Output as a markdown FAQ with 4-6 Q&A pairs. Each question "
            "is an H3, each answer 2-4 sentences."
        )
    if fmt == ContentFormat.REDDIT_ANSWER.value:
        return (
            "Output as a single Reddit-style answer, conversational, "
            "300-500 words, no headings."
        )
    if fmt == ContentFormat.JSON_LD.value:
        return (
            "Output ONLY a JSON-LD object (schema.org) appropriate to the "
            "brief, no markdown, no commentary."
        )
    if fmt == ContentFormat.LANDING_PAGE.value:
        return (
            "Output as a markdown landing page: hero headline, "
            "subhead, three feature blocks, FAQ, CTA."
        )
    if fmt == ContentFormat.META_DESCRIPTION.value:
        return "Output a single meta description, 140-160 characters."
    return (
        "Output as a markdown blog post with an H1 title, intro, "
        "3-5 H2 sections, and a closing summary."
    )


def _build_prompt(brief: ContentBrief) -> tuple[str, str]:
    system = _tone_summary(brief.website)
    structure_json = json.dumps(brief.suggested_structure or {}, indent=2)
    keywords = ", ".join(brief.target_keywords or []) or "n/a"
    user = (
        f"You are drafting content for the brand. The objective:\n"
        f"{brief.headline}\n\n"
        f"Why this matters: {brief.description}\n\n"
        f"Target keywords: {keywords}\n\n"
        f"Suggested structure (use as guidance):\n{structure_json}\n\n"
        f"{_facts_block(brief)}\n\n"
        f"{_format_instructions(brief.target_format)}"
    )
    return system, user


def _call_anthropic(system: str, user_prompt: str, *, website=None) -> str:
    """Call Claude via the core gateway. Empty string on any failure so
    the caller falls back to the deterministic stub. ``website``
    attributes the token spend to the tenant in core.ai_tracking."""
    provider = ClaudeUtility(
        model=getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        max_tokens=2048,
    )
    if not provider.is_configured():
        # No API key is the normal stub path in dev/tests — stay silent.
        return ""
    result = provider.query(
        user_prompt,
        system_prompt=system,
        user=getattr(website, "user", None),
        website=website,
        module="content_studio",
        role="drafting",
    )
    if not result.succeeded:
        logger.warning("Anthropic drafting call failed: %s", result.error)
        return ""
    return result.text


def _stub_body(brief: ContentBrief) -> str:
    """Deterministic draft used in tests / dev without an API key."""
    sections = (brief.suggested_structure or {}).get("sections") or []
    lines = [f"# {brief.headline}", "", brief.description, ""]
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        heading = sec.get("heading") or "Section"
        summary = sec.get("summary") or ""
        lines.append(f"## {heading}")
        lines.append(summary or "Placeholder content drawn from the grounded facts.")
        lines.append("")
    facts = list(brief.grounded_facts.all()[:5])
    if facts:
        lines.append("## Sources")
        for f in facts:
            lines.append(f"- {f.subject} {f.predicate} {f.object}")
    return "\n".join(lines).strip() + "\n"


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def draft_content(brief_id: str, regenerate: bool = False) -> ContentDraft:
    """Generate a draft for a :class:`ContentBrief`.

    If ``regenerate`` is True a new draft row is created with the next
    revision number; otherwise a fresh first revision is created.
    """
    brief = ContentBrief.objects.select_related("website").get(id=brief_id)
    system, user = _build_prompt(brief)

    body = _call_anthropic(system, user, website=brief.website) or _stub_body(brief)

    if brief.target_format == ContentFormat.JSON_LD.value:
        try:
            json_ld = json.loads(re.search(r"\{.*\}", body, re.DOTALL).group(0))
        except Exception:
            json_ld = {"@context": "https://schema.org", "@type": "Article",
                       "headline": brief.headline}
        body_markdown = "```json\n" + json.dumps(json_ld, indent=2) + "\n```"
    else:
        json_ld = None
        body_markdown = body

    revision = 1
    if regenerate:
        last = brief.drafts.order_by("-revision").first()
        if last is not None:
            revision = (last.revision or 0) + 1

    title_match = re.search(r"^#\s+(.+)$", body_markdown, re.MULTILINE)
    title = (title_match.group(1) if title_match else brief.headline)[:400]

    draft = ContentDraft.objects.create(
        brief=brief,
        website=brief.website,
        title=title,
        body_markdown=body_markdown,
        json_ld=json_ld,
        word_count=_word_count(body_markdown),
        status=DraftStatus.GENERATING.value,
        revision=revision,
    )

    try:
        v_score, v_notes = voice_guard.score_voice(draft)
    except Exception as exc:
        logger.warning("voice_guard failed: %s", exc)
        v_score, v_notes = None, ""
    try:
        a_score, a_notes = accuracy_guard.score_accuracy(draft)
    except Exception as exc:
        logger.warning("accuracy_guard failed: %s", exc)
        a_score, a_notes = None, ""

    draft.voice_score = v_score
    draft.voice_notes = v_notes or ""
    draft.accuracy_score = a_score
    draft.accuracy_notes = a_notes or ""
    draft.status = DraftStatus.READY.value
    draft.save(update_fields=[
        "voice_score", "voice_notes",
        "accuracy_score", "accuracy_notes",
        "status", "updated_at",
    ])

    if brief.status == BriefStatus.OPEN.value:
        brief.status = BriefStatus.DRAFTED.value
        brief.save(update_fields=["status", "updated_at"])

    return draft
