"""
LLM-generated "why it matters" rationales per citation.

The previous build_why_it_matters heuristic produced templated strings like
"Relevant to this clinical scenario in felines" whenever no intext quote or
abstract quote could be extracted. That felt generic and hurt the perceived
evidence transparency score.

This module issues ONE batched Haiku call that rationalises every citation
in the answer at once and returns a JSON map of ref → short claim-grounded
rationale. Haiku is fast (~500ms end-to-end) and cheap; the total call cost
per answer is tiny compared to the main Sonnet generation.

Fallback chain (applied in caller):
  1. LLM rationale (this module)
  2. Heuristic: intext_passage (sentence from answer citing [N])
  3. Heuristic: relevant_quote (best abstract sentence)
  4. Template: build_why_it_matters (study-type driven)

Skipped when `evidence_mode == "consensus"` (no sources to ground against).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.models.chat import CitationItem
from app.services.claude_service import ClaudeService

_log = logging.getLogger(__name__)

_WHY_SYSTEM = (
    "You are a veterinary evidence analyst. For each numbered citation in the "
    "batch, write ONE short rationale (≤22 words) explaining how that specific "
    "source supports the clinician's question. The rationale must be grounded "
    "in the source's title + abstract snippet and tied to a concrete clinical "
    "claim when possible. Avoid generic phrasing like 'Relevant to this scenario' "
    "or 'Supports the recommendation' — be specific about the mechanism, drug, "
    "dose, monitoring interval, or diagnostic finding that the source contributes.\n\n"
    "Return ONLY a single JSON object keyed by the citation's ref number (as a "
    "string), value = the rationale string. No markdown, no commentary, no code "
    "fences. If you cannot ground a rationale for a citation, omit that key "
    "entirely — the caller will fall back to a template.\n\n"
    "Example output: "
    '{"1":"Retrospective canine pyometra cohort supports early IVFT + broad-spectrum antimicrobial cover before OVH.",'
    '"3":"ACVIM consensus on sepsis bundles guides lactate-directed resuscitation in septic dogs."}'
)

# Guard rails — Haiku will occasionally emit hedging prose even when told
# not to. Reject rationales that are (a) too short, (b) too long, or (c)
# obviously template-shaped. The caller's fallback chain picks up the rest.
_MIN_LEN = 25
_MAX_LEN = 240
_TEMPLATE_SMELL = re.compile(
    r"^(relevant to|supports? the|provides? context|general overview)",
    re.I,
)


def _extract_snippet(citation: CitationItem, max_chars: int = 600) -> str:
    """Title + abstract (trimmed) for grounding. Trimmed aggressively so
    the batched call stays cheap even with 10+ citations."""
    abstract = (citation.abstract or "").strip()
    if len(abstract) > max_chars:
        # Head + tail slice preserves opening context and concluding claims
        head = abstract[: int(max_chars * 0.7)]
        tail = abstract[-(max_chars - len(head) - 20):]
        abstract = f"{head}… {tail}"
    return f'"{citation.title}" — {abstract}'.strip()


def _build_batch_prompt(query: str, citations: list[CitationItem]) -> str:
    parts: list[str] = [f"Clinician's question: {query.strip()}\n\nCitations:"]
    for c in citations:
        parts.append(f"[{c.ref}] {_extract_snippet(c)}")
    parts.append(
        "\nFor each ref above, output the JSON map of ref → rationale. "
        "Omit refs you cannot ground."
    )
    return "\n\n".join(parts)


def _parse_response(text: str) -> dict[int, str]:
    """Tolerant JSON parser — strips code fences and bad leading text."""
    if not text:
        return {}
    stripped = text.strip()
    # Remove any markdown fencing Haiku may emit
    if stripped.startswith("```"):
        parts = stripped.split("```")
        if len(parts) >= 2:
            stripped = parts[1].lstrip("json").strip()
    # Last-resort: locate the first { and last } to carve out the object
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return {}
    blob = stripped[first: last + 1]
    try:
        raw: Any = json.loads(blob)
    except json.JSONDecodeError:
        return {}
    out: dict[int, str] = {}
    if not isinstance(raw, dict):
        return {}
    for k, v in raw.items():
        try:
            ref = int(str(k).strip())
        except ValueError:
            continue
        if not isinstance(v, str):
            continue
        rationale = v.strip().rstrip(".") + "."
        if not (_MIN_LEN <= len(rationale) <= _MAX_LEN):
            continue
        if _TEMPLATE_SMELL.match(rationale):
            continue
        out[ref] = rationale
    return out


_HAIKU_MODEL = "claude-haiku-4-5"
# Scale max_tokens with the number of citations. ≤22 words × ~1.3 tok/word
# × 10 citations ≈ 300 tokens; add headroom for JSON key/braces overhead.
_BASE_MAX_TOKENS = 200
_PER_CITATION_TOKENS = 60


def generate_rationales(
    query: str,
    citations: list[CitationItem],
    claude: ClaudeService,
) -> dict[int, str]:
    """
    Returns a map of citation.ref → rationale. Empty dict on failure.
    Caller overlays these on top of the heuristic why_it_matters — any
    missing refs keep the heuristic text.
    """
    if not citations:
        return {}
    # Only pass citations with a non-trivial abstract or title; no grounding
    # possible from title alone for the shortest stubs.
    graded = [c for c in citations if (c.title or "").strip()]
    if not graded:
        return {}

    prompt = _build_batch_prompt(query, graded)
    max_tokens = _BASE_MAX_TOKENS + _PER_CITATION_TOKENS * len(graded)

    try:
        # Re-use the underlying Anthropic client from the main ClaudeService
        # instance (same API key, same HTTP connection pool) but pin Haiku
        # for this small-batch rationale task.
        response = claude._client.messages.create(  # noqa: SLF001
            model=_HAIKU_MODEL,
            max_tokens=max_tokens,
            system=_WHY_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else ""
    except Exception as exc:
        _log.warning("why_it_matters Haiku call failed (non-fatal): %s", exc)
        return {}

    return _parse_response(text)


def overlay(
    citations: list[CitationItem],
    rationales: dict[int, str],
) -> None:
    """Overwrite heuristic why_it_matters with LLM rationale where provided."""
    if not rationales:
        return
    for c in citations:
        r = rationales.get(c.ref)
        if r:
            c.why_it_matters = r
