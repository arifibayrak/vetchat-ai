"""
Post-retrieval enrichment for citations — two-axis evidence model.

We classify every citation along two orthogonal axes:

  1. relevance  — how directly this source answers the user's query
                  ("direct" | "related" | "background" | "tangential")
                  Derived from the cross-encoder rerank score, with a small
                  boost from query↔title word overlap so that a perfectly
                  on-topic title can lift "related" to "direct".

  2. strength   — the study-design quality of the source itself
                  ("guideline" | "systematic_review" | "clinical_study" |
                   "case_series" | "narrative_review" | "expert_consensus")
                  Derived from the title/abstract/doc_type.

These replace the previous single `evidence_tier` field, which tangled the
two dimensions together (and had "review" appearing in two separate
branches of the classifier). Keeping them separate means an indirectly-
matched RCT is no longer silently downgraded to "weak", and a highly-
relevant narrative review is no longer silently promoted to "direct".

We also populate two clinician-friendly display fields:
  - study_type          — human-readable label built from the same regex set
  - species_relevance   — "Dogs" | "Cats" | "Equine" | ...

No LLM calls here; WS3 (why_it_matters.py) does that separately.
"""
from __future__ import annotations

import re

from app.models.chat import CitationItem

# ─────────────────────────────────────────────────────────────────────────────
# Study-type classification — human-readable label for the metadata row
# ─────────────────────────────────────────────────────────────────────────────

_STUDY_TYPE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Guideline / consensus statements first — they win over "review"
    (re.compile(r"\b(ACVIM|WSAVA|IRIS|ISFM|AAHA|BSAVA)[\s:-]*(consensus|guidelin|statement|position)", re.I), "Guideline"),
    (re.compile(r"\bconsensus\s+(statement|guideline|panel)", re.I), "Guideline"),
    (re.compile(r"\bclinical\s+practice\s+guideline", re.I), "Guideline"),
    # Systematic reviews / meta-analyses
    (re.compile(r"\b(systematic\s+review|meta[-\s]?analysis)\b", re.I), "Systematic review"),
    # RCTs
    (re.compile(r"\brandomi[sz]ed\b.*\btrial\b", re.I), "RCT"),
    (re.compile(r"\bdouble[-\s]blind", re.I), "RCT"),
    # Prospective observational
    (re.compile(r"\bprospective\b.*\b(study|cohort|observational)", re.I), "Prospective study"),
    # Retrospective
    (re.compile(r"\bretrospective\b", re.I), "Retrospective study"),
    # Case series / reports
    (re.compile(r"\bcase\s+series\b", re.I), "Case series"),
    (re.compile(r"\bcase\s+reports?\b", re.I), "Case report"),
    # General reviews (narrative)
    (re.compile(r"\breview\b", re.I), "Review"),
    # Experimental / in vitro / laboratory
    (re.compile(r"\bin\s+vitro\b", re.I), "In vitro study"),
    (re.compile(r"\bexperimental\b", re.I), "Experimental study"),
]

_DOC_TYPE_MAP: dict[str, str] = {
    "re": "Review",
    "review": "Review",
    "ar": "Research article",
    "article": "Research article",
    "cp": "Conference paper",
    "ch": "Book chapter",
    "ed": "Editorial",
    "le": "Letter",
    "no": "Note",
}


def classify_study_type(citation: CitationItem, extra_text: str = "") -> str:
    """Infer a study-type label (used purely for display) from title+abstract+doc_type."""
    dt = (citation.doc_type or "").strip().lower()
    if dt in _DOC_TYPE_MAP:
        # Still let title override doc_type for consensus/guideline/review detection
        pattern_hit = _scan_patterns(citation.title + " " + extra_text)
        if pattern_hit:
            return pattern_hit
        return _DOC_TYPE_MAP[dt]

    scan = f"{citation.title} {citation.abstract} {extra_text}"
    return _scan_patterns(scan) or "Research article"


def _scan_patterns(text: str) -> str:
    for pat, label in _STUDY_TYPE_PATTERNS:
        if pat.search(text):
            return label
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Species relevance — used in the card metadata row
# ─────────────────────────────────────────────────────────────────────────────

_SPECIES_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(dogs?|canine|canines|canis\s+familiaris|puppy|puppies)\b", re.I), "Dogs"),
    (re.compile(r"\b(cats?|feline|felines|felis\s+catus|kitten|kittens)\b", re.I), "Cats"),
    (re.compile(r"\b(horses?|equine|equines|equus\s+caballus|foal|mare|stallion)\b", re.I), "Equine"),
    (re.compile(r"\b(cattle|bovine|calf|calves|cow|cows|bulls?|heifer)\b", re.I), "Bovine"),
    (re.compile(r"\b(birds?|avian|parrots?|psittacine)\b", re.I), "Avian"),
    (re.compile(r"\b(rabbits?|ferrets?|guinea\s+pigs?|reptiles?|exotic\s+pets?)\b", re.I), "Exotic"),
]


def classify_species(citation: CitationItem, extra_text: str = "") -> str:
    """Return a short species label like 'Dogs', 'Dogs & cats', or ''."""
    scan = f"{citation.title} {citation.abstract} {extra_text}"
    hits: list[str] = []
    for pat, label in _SPECIES_PATTERNS:
        if pat.search(scan) and label not in hits:
            hits.append(label)

    if not hits:
        return ""
    if len(hits) == 1:
        return hits[0]
    if set(hits) == {"Dogs", "Cats"}:
        return "Dogs & cats"
    if len(hits) == 2:
        return " & ".join(hits)
    return "Mixed species"


# ─────────────────────────────────────────────────────────────────────────────
# Axis 1: relevance — how directly the source answers the query
# Values (ordered strongest → weakest):
#   direct     — high semantic match AND meaningful query-word overlap
#   related    — positive semantic match OR some query-word overlap
#   background — marginal match, retrieved but tangentially useful
#   tangential — scraped through the reranker floor only
# ─────────────────────────────────────────────────────────────────────────────

_RELEVANCE_STRONG  = 1.5   # rerank_score threshold for "direct" (needs overlap too)
_RELEVANCE_POSITIVE = 0.0  # rerank_score threshold for "related" floor
_RELEVANCE_BACKGROUND = -1.0

_STOP = frozenset({
    "the", "a", "an", "and", "or", "in", "of", "to", "for", "with", "at", "by",
    "from", "is", "are", "was", "were", "that", "this", "it", "as", "on", "be",
    "been", "has", "have", "had", "not", "but", "its", "which", "may", "also",
    "we", "how", "what", "when", "why", "where", "can", "could", "should",
    "would", "about", "into", "against", "during", "before", "after", "between",
    "under", "over", "up", "down", "out", "off", "through", "new", "old",
    "i", "my", "your", "their",
})


def _content_tokens(text: str) -> set[str]:
    """Lowercase word-level tokens with stopwords removed. Small-set ops only."""
    return {
        t for t in re.findall(r"[a-z][a-z\-]{2,}", (text or "").lower())
        if t not in _STOP
    }


def classify_relevance(
    rerank_score: float,
    query: str,
    citation: CitationItem,
) -> str:
    """
    Two-step rule:
      1. Use rerank_score to pick the base bucket (direct/related/background/tangential).
      2. Apply a small +/- shift based on query↔(title+abstract) word overlap
         so that a very on-topic title can lift "related" → "direct", and a
         rerank hit with zero lexical overlap drops from "related" → "background".
    """
    query_tokens = _content_tokens(query)
    scan_text = f"{citation.title} {citation.abstract or ''}"
    source_tokens = _content_tokens(scan_text)
    overlap = len(query_tokens & source_tokens) if query_tokens else 0

    # Base bucket from score
    if rerank_score >= _RELEVANCE_STRONG:
        base = "direct" if overlap >= 1 else "related"
    elif rerank_score >= _RELEVANCE_POSITIVE:
        base = "direct" if overlap >= 2 else "related"
    elif rerank_score >= _RELEVANCE_BACKGROUND:
        base = "related" if overlap >= 2 else "background"
    else:
        base = "tangential"

    return base


_RELEVANCE_LABELS = {
    "direct":     "Direct",
    "related":    "Related",
    "background": "Background",
    "tangential": "Tangential",
}


def relevance_label(value: str) -> str:
    return _RELEVANCE_LABELS.get(value, "Related")


# ─────────────────────────────────────────────────────────────────────────────
# Axis 2: strength — the study-design quality of the source itself
# Values (roughly ordered by evidential weight, highest → lowest):
#   guideline, systematic_review, clinical_study, case_series,
#   narrative_review, expert_consensus
# ─────────────────────────────────────────────────────────────────────────────

_STRENGTH_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Guidelines / consensus statements — trump everything else
    (re.compile(r"\b(ACVIM|WSAVA|IRIS|ISFM|AAHA|BSAVA)[\s:-]*(consensus|guidelin|statement|position)", re.I), "guideline"),
    (re.compile(r"\bconsensus\s+(statement|guideline|panel)", re.I), "guideline"),
    (re.compile(r"\bclinical\s+practice\s+guideline", re.I), "guideline"),
    # Systematic review / meta-analysis
    (re.compile(r"\b(systematic\s+review|meta[-\s]?analysis)\b", re.I), "systematic_review"),
    # Primary clinical studies
    (re.compile(r"\brandomi[sz]ed\b.*\btrial\b", re.I), "clinical_study"),
    (re.compile(r"\b(double[-\s]blind|controlled\s+trial|clinical\s+trial)\b", re.I), "clinical_study"),
    (re.compile(r"\bprospective\b.*\b(study|cohort|observational|trial)", re.I), "clinical_study"),
    (re.compile(r"\bretrospective\b.*\b(study|cohort|case\s+series|review|analysis)\b", re.I), "clinical_study"),
    (re.compile(r"\bretrospective\b", re.I), "clinical_study"),
    (re.compile(r"\bexperimental\b.*\b(study|model|infection)\b", re.I), "clinical_study"),
    # Case series / reports
    (re.compile(r"\bcase\s+series\b", re.I), "case_series"),
    (re.compile(r"\bcase\s+reports?\b", re.I), "case_series"),
    # Narrative review (catch-all for "review" that isn't a systematic review)
    (re.compile(r"\breview\b", re.I), "narrative_review"),
]

_DOC_TYPE_TO_STRENGTH = {
    "re":      "narrative_review",
    "review":  "narrative_review",
    "ar":      "clinical_study",   # "article" → treat as primary research by default
    "article": "clinical_study",
    "cp":      "narrative_review", # conference paper — narrative-grade unless title says otherwise
    "ch":      "narrative_review", # book chapter → textbook knowledge
    "ed":      "expert_consensus", # editorial
    "le":      "expert_consensus", # letter
    "no":      "expert_consensus", # note
}


def classify_strength(citation: CitationItem, extra_text: str = "") -> str:
    """
    Prefer explicit design patterns from title/abstract.
    Fall back to doc_type, then to expert_consensus.
    """
    scan = f"{citation.title} {citation.abstract} {extra_text}"
    for pat, label in _STRENGTH_PATTERNS:
        if pat.search(scan):
            return label

    dt = (citation.doc_type or "").strip().lower()
    if dt in _DOC_TYPE_TO_STRENGTH:
        return _DOC_TYPE_TO_STRENGTH[dt]

    return "expert_consensus"


_STRENGTH_LABELS = {
    "guideline":         "Guideline",
    "systematic_review": "Systematic review",
    "clinical_study":    "Clinical study",
    "case_series":       "Case series",
    "narrative_review":  "Narrative review",
    "expert_consensus":  "Expert consensus",
}


def strength_label(value: str) -> str:
    return _STRENGTH_LABELS.get(value, "Expert consensus")


# ─────────────────────────────────────────────────────────────────────────────
# "Why it matters" — heuristic fallback (WS3 replaces the main path with an
# LLM call via why_it_matters.py; this remains the last-resort template).
# ─────────────────────────────────────────────────────────────────────────────

_MAX_WHY_LEN = 180


def _looks_like_reference_dump(text: str, author_prefix: str = "") -> bool:
    stripped = text.strip()
    if len(stripped.split()) <= 5 and re.search(r"\bet\s+al\b", stripped, re.I):
        return True
    if re.fullmatch(r"\[?\d+\]?\s*[A-Z][a-z]+(\s+[A-Z])?\s*(et\s+al\.?)?\s*\(?\d{0,4}\)?\s*\.?", stripped, re.I):
        return True
    if author_prefix and stripped.lower().startswith(author_prefix.lower()) and len(stripped) < 40:
        return True
    return False


def build_why_it_matters(citation: CitationItem) -> str:
    for source in (citation.intext_passage, citation.relevant_quote):
        text = (source or "").strip()
        if not text:
            continue
        if _looks_like_reference_dump(text, citation.authors):
            continue
        text = re.sub(r"\[\d+\]|\[(Consensus|Gap|Direct evidence|Review|Guideline/Consensus|Weak indirect|No direct evidence)\]", "", text)
        text = re.sub(r"\s+", " ", text).strip().lstrip("▸•-— ").strip()
        if len(text) < 20:
            continue
        if len(text) > _MAX_WHY_LEN:
            text = text[: _MAX_WHY_LEN - 1].rsplit(" ", 1)[0] + "…"
        return text

    # Template fallback — keeps the card informative even without a quote.
    # WS3 overlays an LLM-generated claim-grounded rationale on top of this
    # whenever the Haiku call succeeds.
    strength = citation.strength or ""
    species = citation.species_relevance or "veterinary patients"
    if strength == "guideline":
        return f"Guideline cited for standard-of-care practice in {species}."
    if strength == "systematic_review":
        return f"Systematic review summarising pooled evidence in {species}."
    if strength == "clinical_study":
        return f"Primary clinical data in {species} relevant to this scenario."
    if strength == "case_series":
        return f"Case series documenting clinical course and outcome in {species}."
    if strength == "narrative_review":
        return f"Narrative review summarising current practice in {species}."
    return f"Background reference supporting this topic in {species}."


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def enrich(citations: list[CitationItem], query: str = "") -> list[CitationItem]:
    """
    Populate, for each citation:
      - study_type, species_relevance (display helpers)
      - strength  (study-design axis)
      - relevance (query-match axis)
      - why_it_matters (heuristic fallback; WS3 overrides when available)
    Order matters: relevance/strength must be set before build_why_it_matters
    so the template fallback can reference them.
    """
    for c in citations:
        c.study_type = c.study_type or classify_study_type(c, extra_text=query)
        c.species_relevance = c.species_relevance or classify_species(c, extra_text=query)
        c.strength = c.strength or classify_strength(c, extra_text=query)
        c.relevance = c.relevance or classify_relevance(
            rerank_score=c.rerank_score,
            query=query,
            citation=c,
        )
        c.why_it_matters = c.why_it_matters or build_why_it_matters(c)
    return citations


_RELEVANCE_ORDER = ("direct", "related", "background", "tangential")
_STRENGTH_ORDER = (
    "guideline", "systematic_review", "clinical_study",
    "case_series", "narrative_review", "expert_consensus",
)


def counts_by_axes(citations: list[CitationItem]) -> dict:
    """
    Returns the shape the frontend summary strip expects:
      {
        "relevance": {"direct": 2, "related": 3, ...},
        "strength":  {"clinical_study": 3, "guideline": 1, ...},
      }
    Only non-zero buckets are included, in the fixed display order above.
    """
    rel: dict[str, int] = {}
    strg: dict[str, int] = {}
    for c in citations:
        r = c.relevance or "related"
        s = c.strength or "expert_consensus"
        rel[r] = rel.get(r, 0) + 1
        strg[s] = strg.get(s, 0) + 1

    return {
        "relevance": {k: rel[k] for k in _RELEVANCE_ORDER if rel.get(k)},
        "strength":  {k: strg[k] for k in _STRENGTH_ORDER if strg.get(k)},
    }
