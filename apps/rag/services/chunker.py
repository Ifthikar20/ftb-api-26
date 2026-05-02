"""
Text chunking for the RAG knowledge base.

Splits a long body of text (a scraped page, an audit response, etc.) into
overlapping segments that fit within an embedding-model context window.

We don't ship a real tokenizer — token counts are approximated as words / 0.75
(English averages ~1.3 tokens per word). That's accurate enough to keep
chunks safely under any embedding model's input limit, and avoids pulling
tiktoken into the runtime.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Heuristic words->tokens conversion for English. Embedding models all
# accept far more than this per chunk, but smaller chunks give cleaner
# retrieval (one idea per chunk).
_DEFAULT_TARGET_WORDS = 300
_DEFAULT_OVERLAP_WORDS = 40

# Section delimiters we respect when chunking. A blank line, a markdown
# heading, or one of the explicit markers used by content_enricher
# (=== HEADING ===) all start a new logical section.
_SECTION_RE = re.compile(
    r"(?:^|\n)(?:===\s*[^=\n]+\s*===|#{1,6}\s+[^\n]+|---+)\n",
    re.MULTILINE,
)


@dataclass
class Chunk:
    text: str
    section_label: str = ""
    token_count: int = 0


def _approx_tokens(words: int) -> int:
    return max(1, int(words / 0.75))


def chunk_text(
    text: str,
    *,
    target_words: int = _DEFAULT_TARGET_WORDS,
    overlap_words: int = _DEFAULT_OVERLAP_WORDS,
    default_label: str = "",
) -> list[Chunk]:
    """Return a list of Chunks covering ``text`` with the given overlap.

    Sections are detected from explicit markers (=== HEADING ===,
    markdown headings, ---). Each section is then sliced into
    word-windowed chunks with overlap so retrieval can stitch
    neighbouring context together.
    """
    if not text or not text.strip():
        return []

    sections = _split_sections(text, default_label)
    chunks: list[Chunk] = []

    for label, body in sections:
        words = body.split()
        if not words:
            continue
        if len(words) <= target_words:
            chunks.append(Chunk(
                text=" ".join(words),
                section_label=label,
                token_count=_approx_tokens(len(words)),
            ))
            continue

        step = max(1, target_words - overlap_words)
        for start in range(0, len(words), step):
            window = words[start:start + target_words]
            if not window:
                break
            chunks.append(Chunk(
                text=" ".join(window),
                section_label=label,
                token_count=_approx_tokens(len(window)),
            ))
            if start + target_words >= len(words):
                break

    return chunks


def _split_sections(text: str, default_label: str) -> list[tuple[str, str]]:
    """Split text into (label, body) sections by recognised delimiters."""
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return [(default_label, text.strip())]

    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        head = text[:matches[0].start()].strip()
        if head:
            sections.append((default_label, head))

    for i, match in enumerate(matches):
        header = match.group(0).strip()
        # Clean the header into a label
        label = header.strip("=#- \n").strip()
        if not label:
            label = default_label
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            sections.append((label, body))

    return sections
