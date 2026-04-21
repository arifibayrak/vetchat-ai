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


# ─────────────────────────────────────────────────────────────────────────────
# Tier A — DEEP rationale for DIRECT citations (WS10, 2026-04-21)
# One Haiku call per direct citation, parallelised via ThreadPoolExecutor.
# ~50-word two-sentence rationale that (a) states what the source
# establishes, (b) names which specific claim in Claude's answer it supports.
# ─────────────────────────────────────────────────────────────────────────────

_DEEP_WHY_SYSTEM = (
    "You are a veterinary evidence analyst. For this ONE citation, write a "
    "two-sentence rationale (≤50 words total) for the clinician reading the "
    "answer:\n"
    "  Sentence 1 — what the source establishes (mechanism, finding, dose, "
    "monitoring interval, or recommendation). Be specific — name the drug / "
    "value / interval.\n"
    "  Sentence 2 — which specific claim in the clinician's answer this "
    "source supports. If a specific sentence from the answer cited this "
    "reference, quote or paraphrase its clinical point. Use the intext "
    "passage when supplied.\n\n"
    "Rules:\n"
    "  - Do not repeat the title verbatim.\n"
    "  - Do not start with 'This source', 'This paper', 'This study', "
    "'The authors', or 'Relevant to'.\n"
    "  - Do not hedge ('may support', 'could help'). State plainly.\n"
    "  - Output ONLY the rationale text. No preamble. No markdown. No "
    "citation markers."
)

# Single-citation call — cheap, parallelisable. Keep room for 60 words of
# prose (~80 tokens) plus Haiku's safety margin.
_DEEP_MAX_TOKENS = 160
# Cost guard — don't spin up more than this many direct rationales per
# answer. If more than 6 direct citations, the remainder fall through to
# the batched Tier B rationale.
_DEEP_CAP = 6
# Length sanity — Tier A rationales should be noticeably longer than Tier B.
# 35–60 words ≈ 180–360 characters.
_DEEP_MIN_LEN = 120
_DEEP_MAX_LEN = 360


def _build_deep_prompt(
    query: str,
    citation: CitationItem,
    answer_body: str,
) -> str:
    # Pull the exact sentence(s) from the answer that cite [N] — this is
    # the single most useful grounding signal for Tier A. Fall back to the
    # heuristic intext_passage already extracted in chat.py.
    intext = (citation.intext_passage or "").strip()
    abstract = (citation.abstract or "").strip()
    if len(abstract) > 700:
        abstract = abstract[:700] + "…"

    parts = [f"Clinician's question:\n{query.strip()}"]
    if intext:
        parts.append(f"Sentence in the answer that cited [{citation.ref}]:\n{intext}")
    parts.append(
        f"Citation [{citation.ref}] — title + abstract:\n"
        f'"{citation.title}" — {abstract}'
    )
    parts.append(
        "Write the two-sentence ≤50-word rationale now. "
        "Output ONLY the rationale."
    )
    return "\n\n".join(parts)


def _clean_deep(text: str) -> str:
    """Strip preamble, code fences, citation markers; normalise whitespace."""
    if not text:
        return ""
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            t = parts[1].lstrip("json").strip()
    # Kill leading labels Haiku sometimes emits
    t = re.sub(r"^\s*(Rationale|Answer|Summary)\s*:\s*", "", t, flags=re.I)
    t = re.sub(r"\[\d+\]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _call_deep_one(
    query: str,
    citation: CitationItem,
    answer_body: str,
    claude: ClaudeService,
) -> str | None:
    try:
        response = claude._client.messages.create(  # noqa: SLF001
            model=_HAIKU_MODEL,
            max_tokens=_DEEP_MAX_TOKENS,
            system=_DEEP_WHY_SYSTEM,
            messages=[{
                "role": "user",
                "content": _build_deep_prompt(query, citation, answer_body),
            }],
        )
        text = response.content[0].text if response.content else ""
    except Exception as exc:
        _log.warning("deep why call failed for ref %s (non-fatal): %s", citation.ref, exc)
        return None

    cleaned = _clean_deep(text)
    if not cleaned:
        return None
    if not (_DEEP_MIN_LEN <= len(cleaned) <= _DEEP_MAX_LEN):
        # Too short (<35 words) or too long (>60) — reject so caller falls
        # back to Tier B. Prevents Haiku one-liners shorter than the batched
        # Tier B rationale from replacing a better existing one.
        _log.info(
            "deep why rejected for ref %s: length %d outside [%d, %d]",
            citation.ref, len(cleaned), _DEEP_MIN_LEN, _DEEP_MAX_LEN,
        )
        return None
    # Template-smell guard reused from Tier B
    if _TEMPLATE_SMELL.match(cleaned):
        return None
    return cleaned


def generate_deep_rationales(
    query: str,
    citations: list[CitationItem],
    claude: ClaudeService,
    answer_body: str,
) -> dict[int, str]:
    """
    Tier A: deep ~50-word claim-linked rationales for DIRECT citations only.
    Parallelised via ThreadPoolExecutor (each call is independent). Capped
    at _DEEP_CAP to prevent latency/cost blow-up on answers with many direct
    refs — the remainder stay on Tier B (batched ≤22-word rationales).

    Returns {ref → rationale}. Caller uses overlay() to apply.
    """
    direct = [c for c in citations if (c.relevance or "") == "direct" and (c.title or "").strip()]
    if not direct:
        return {}
    # Apply the cost cap — prioritise the highest-scoring direct citations.
    direct.sort(key=lambda c: -(c.rerank_score or 0.0))
    direct = direct[:_DEEP_CAP]

    from concurrent.futures import ThreadPoolExecutor, as_completed

    out: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=min(len(direct), 6)) as pool:
        fut_to_ref = {
            pool.submit(_call_deep_one, query, c, answer_body, claude): c.ref
            for c in direct
        }
        for fut in as_completed(fut_to_ref):
            ref = fut_to_ref[fut]
            try:
                r = fut.result()
            except Exception as exc:
                _log.warning("deep why future failed for ref %s: %s", ref, exc)
                continue
            if r:
                out[ref] = r
    return out
