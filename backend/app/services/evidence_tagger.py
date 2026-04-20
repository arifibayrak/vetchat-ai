"""
Post-retrieval enrichment for citations.

Infers clinician-friendly metadata from raw retrieval fields so the reference
panel can render "Thompson et al. 2021 — JVECC · Review article · Dogs" instead
of leading with DOI clutter.

Populated fields (all best-effort string heuristics):
  - study_type      — Review | RCT | Case series | Retrospective | Guideline | Research article
  - species_relevance — Dogs | Cats | Dogs & cats | Equine | Avian | Exotic | Mixed | ""
  - evidence_tier   — direct | review | guideline | weak | none
  - why_it_matters  — one-line practitioner-facing summary of what the source supports

No LLM calls — pure string heuristics so this stays fast and cheap.
"""
from __future__ import annotations

import re

from app.models.chat import CitationItem

# ─────────────────────────────────────────────────────────────────────────────
# Study-type classification
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
    """Infer a study type from title + abstract + doc_type metadata."""
    # Trust explicit doc_type if mapped
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
# Species relevance
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
    # Collapse Dogs + Cats → "Dogs & cats"
    if set(hits) == {"Dogs", "Cats"}:
        return "Dogs & cats"
    if len(hits) == 2:
        return " & ".join(hits).replace(" & ", " & ").lower().capitalize() if False else " & ".join(hits)
    return "Mixed species"


# ─────────────────────────────────────────────────────────────────────────────
# Evidence tier — maps relevance + study_type to one of:
#   direct | review | guideline | weak | none
# These are the tags the UI badges near each source card AND that the system
# prompt is instructed to emit inline next to claims.
# ─────────────────────────────────────────────────────────────────────────────

def classify_evidence_tier(citation: CitationItem) -> str:
    relevance = (citation.relevance or "").lower()
    study = (citation.study_type or "").lower()

    if "guideline" in study:
        return "guideline"
    if "review" in study:  # covers "review" and "systematic review"
        return "review"
    if relevance == "high":
        return "direct"
    if relevance == "moderate":
        return "weak"
    if relevance == "tangential":
        return "weak"
    return "direct" if relevance == "" else "weak"


_TIER_LABELS: dict[str, str] = {
    "direct": "Direct evidence",
    "review": "Review article",
    "guideline": "Guideline / Consensus",
    "weak": "Weak indirect evidence",
    "none": "No direct evidence",
}


def tier_label(tier: str) -> str:
    return _TIER_LABELS.get(tier, "Direct evidence")


# ─────────────────────────────────────────────────────────────────────────────
# "Why it matters" — one-line practitioner summary
# Prefers the relevant_quote (already extracted from abstract), else the
# intext_passage (sentence from Claude's answer that cites [N]), else a
# reasonable default built from the study type.
# ─────────────────────────────────────────────────────────────────────────────

_MAX_WHY_LEN = 180


def _looks_like_reference_dump(text: str, author_prefix: str = "") -> bool:
    """
    Detect fragments that are just a References-section echo like
    "[2] Bandaranayaka et al." — these are useless as why_it_matters.
    """
    stripped = text.strip()
    # Bare "author et al." or "author et al. (year)" with no clinical content
    if len(stripped.split()) <= 5 and re.search(r"\bet\s+al\b", stripped, re.I):
        return True
    # Matches the References line format
    if re.fullmatch(r"\[?\d+\]?\s*[A-Z][a-z]+(\s+[A-Z])?\s*(et\s+al\.?)?\s*\(?\d{0,4}\)?\s*\.?", stripped, re.I):
        return True
    # Starts with author prefix + nothing else substantive
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
        # Strip citation markers and bullet glyphs
        text = re.sub(r"\[\d+\]|\[(Consensus|Gap|Direct evidence|Review|Guideline/Consensus|Weak indirect|No direct evidence)\]", "", text)
        text = re.sub(r"\s+", " ", text).strip().lstrip("▸•-— ").strip()
        if len(text) < 20:
            continue
        if len(text) > _MAX_WHY_LEN:
            text = text[: _MAX_WHY_LEN - 1].rsplit(" ", 1)[0] + "…"
        return text

    # Default by study type — keeps the card informative even without quotes
    st = citation.study_type or ""
    species = citation.species_relevance or "veterinary patients"
    if "Guideline" in st:
        return f"{st} cited for standard-of-care practice in {species}."
    if "Review" in st:
        return f"{st} summarising the current evidence base for {species}."
    if "RCT" in st or "trial" in st.lower():
        return f"Controlled trial data in {species} supporting the recommendation."
    if "Retrospective" in st:
        return f"Retrospective case data in {species} relevant to this clinical scenario."
    return f"Relevant to this clinical scenario in {species}."


# ─────────────────────────────────────────────────────────────────────────────
# Public API: one call to enrich every citation in the response.
# ─────────────────────────────────────────────────────────────────────────────

def enrich(citations: list[CitationItem], query: str = "") -> list[CitationItem]:
    """Populate study_type, species_relevance, evidence_tier, why_it_matters."""
    for c in citations:
        c.study_type = c.study_type or classify_study_type(c, extra_text=query)
        c.species_relevance = c.species_relevance or classify_species(c, extra_text=query)
        c.evidence_tier = c.evidence_tier or classify_evidence_tier(c)
        c.why_it_matters = c.why_it_matters or build_why_it_matters(c)
    return citations


def counts_by_tier(citations: list[CitationItem]) -> dict:
    counts: dict[str, int] = {"direct": 0, "review": 0, "guideline": 0, "weak": 0}
    for c in citations:
        tier = c.evidence_tier or "direct"
        counts[tier] = counts.get(tier, 0) + 1
    return counts
