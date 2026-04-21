"""
HyDE-style query expansion.

Short and terse veterinary queries ("lily toxicosis" / "DKA protocol") often
fail to retrieve well because sentence-level embeddings score best against
similarly-shaped text. A literal embedding of "lily toxicosis" matches any
abstract that says "toxicosis" far more than a dedicated feline-lily paper.

HyDE (Hypothetical Document Embeddings, Gao et al. 2022) fixes this by
synthesising a 2–3 sentence pseudo-abstract for the query and embedding
*that*, so retrieval is done in abstract-space instead of query-space.

The chat handler calls `expand(query, claude)` once per turn. We issue a
single short Claude call (~120 tokens) and return the drafted text. The
caller embeds both the raw query and the HyDE text, runs two parallel
Chroma searches, and unions the results before reranking.

Gate with `settings.use_hyde = True` — can be flipped off if latency hurts.
"""
from __future__ import annotations

import logging

from app.services.claude_service import ClaudeService

_log = logging.getLogger(__name__)

_HYDE_SYSTEM = (
    "You are a veterinary research librarian. Given a clinician's question, "
    "draft the OPENING of a hypothetical peer-reviewed veterinary abstract "
    "that would directly answer it. Write as if the abstract were already "
    "published: include species, key mechanisms, diagnostic findings, and "
    "treatment principles in plausible clinical register. "
    "Do NOT cite sources. Do NOT preface with 'Abstract:' or similar. "
    "Output ONLY the abstract text, 2–3 sentences, max 80 words."
)


def expand(query: str, claude: ClaudeService) -> str:
    """
    Return a short hypothetical abstract for this query, or an empty string
    if the call fails. Embedding this alongside the raw query gives the
    retriever a second, more abstract-shaped probe at the corpus.
    """
    if not query or not query.strip():
        return ""
    try:
        response = claude._client.messages.create(  # noqa: SLF001 — same pattern as refine_query
            model=claude._model,
            max_tokens=160,
            system=_HYDE_SYSTEM,
            messages=[{"role": "user", "content": query.strip()}],
        )
        text = response.content[0].text.strip()
        # Collapse any accidental leading boilerplate
        for prefix in ("Abstract:", "abstract:", "Hypothetical abstract:"):
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
        return text
    except Exception as exc:
        _log.warning("HyDE expansion failed, falling back to raw query only: %s", exc)
        return ""
