"""
Unit tests for app.services.evidence_tagger — pure logic, no I/O.

Covers the four classifier outputs a clinician sees on each reference card:
  - study_type        (Review / RCT / Retrospective / Guideline / ...)
  - species_relevance (Dogs / Cats / Dogs & cats / ...)
  - evidence_tier     (direct / review / guideline / weak / none)
  - why_it_matters    (one-line clinician summary)
"""
from app.models.chat import CitationItem
from app.services import evidence_tagger


def _cite(
    title: str = "",
    abstract: str = "",
    doc_type: str = "",
    relevance: str = "high",
    authors: str = "Smith et al.",
    journal: str = "JVIM",
    year: int = 2023,
    intext: str = "",
) -> CitationItem:
    return CitationItem(
        ref=1, title=title, journal=journal, year=year, doi="", url="",
        authors=authors, abstract=abstract, doc_type=doc_type, relevance=relevance,
        intext_passage=intext,
    )


# ─── study_type classification ────────────────────────────────────────────────

def test_classify_guideline_beats_review():
    c = _cite(title="ACVIM Consensus Statement on Chronic Kidney Disease")
    assert evidence_tagger.classify_study_type(c) == "Guideline"


def test_classify_systematic_review():
    c = _cite(title="Systematic review of NSAID toxicity in dogs")
    assert evidence_tagger.classify_study_type(c) == "Systematic review"


def test_classify_rct():
    c = _cite(title="A randomised double-blind trial of meloxicam")
    assert evidence_tagger.classify_study_type(c) == "RCT"


def test_classify_retrospective():
    c = _cite(title="Retrospective analysis of 112 cases of canine parvovirus")
    assert evidence_tagger.classify_study_type(c) == "Retrospective study"


def test_classify_case_series():
    c = _cite(title="Canine pericardial effusion — a case series of 34 dogs")
    assert evidence_tagger.classify_study_type(c) == "Case series"


def test_classify_narrative_review():
    c = _cite(title="Review of feline urethral obstruction management")
    assert evidence_tagger.classify_study_type(c) == "Review"


def test_classify_defaults_to_research_article():
    c = _cite(title="Plasma lactate levels in septic dogs")
    assert evidence_tagger.classify_study_type(c) == "Research article"


def test_doc_type_mapping_used_when_no_pattern_match():
    c = _cite(title="Plasma lactate levels", doc_type="re")
    # "re" doc_type → Review, but title has no study-type pattern so doc_type wins
    assert evidence_tagger.classify_study_type(c) == "Review"


# ─── species relevance ────────────────────────────────────────────────────────

def test_species_dogs_only():
    c = _cite(title="Canine parvovirus vaccination protocols")
    assert evidence_tagger.classify_species(c) == "Dogs"


def test_species_cats_only():
    c = _cite(title="Feline hyperthyroidism management", abstract="A study in cats.")
    assert evidence_tagger.classify_species(c) == "Cats"


def test_species_dogs_and_cats_collapsed():
    c = _cite(title="NSAID use in dogs and cats: a retrospective review")
    assert evidence_tagger.classify_species(c) == "Dogs & cats"


def test_species_equine():
    c = _cite(title="Equine colic surgery outcomes", abstract="Evaluating mares and stallions")
    assert evidence_tagger.classify_species(c) == "Equine"


def test_species_unknown_returns_empty():
    c = _cite(title="Pharmacokinetics of amoxicillin")
    assert evidence_tagger.classify_species(c) == ""


# ─── evidence tier ────────────────────────────────────────────────────────────

def test_tier_guideline_wins_over_high_relevance():
    c = _cite(title="ACVIM Consensus Statement", relevance="high")
    c.study_type = "Guideline"
    assert evidence_tagger.classify_evidence_tier(c) == "guideline"


def test_tier_review_from_study_type():
    c = _cite(title="Review of feline asthma", relevance="moderate")
    c.study_type = "Review"
    assert evidence_tagger.classify_evidence_tier(c) == "review"


def test_tier_high_relevance_no_review_means_direct():
    c = _cite(relevance="high")
    c.study_type = "Research article"
    assert evidence_tagger.classify_evidence_tier(c) == "direct"


def test_tier_moderate_means_weak():
    c = _cite(relevance="moderate")
    c.study_type = "Research article"
    assert evidence_tagger.classify_evidence_tier(c) == "weak"


def test_tier_tangential_means_weak():
    c = _cite(relevance="tangential")
    c.study_type = "Research article"
    assert evidence_tagger.classify_evidence_tier(c) == "weak"


# ─── why_it_matters ───────────────────────────────────────────────────────────

def test_why_strips_citation_markers():
    c = _cite(intext="Remdesivir is effective for FIP in cats [3].")
    out = evidence_tagger.build_why_it_matters(c)
    assert "[3]" not in out
    assert "Remdesivir" in out


def test_why_uses_intext_over_quote():
    c = _cite(intext="Short intext passage from answer.")
    c.relevant_quote = "Much longer relevant abstract quote that would be chosen otherwise."
    out = evidence_tagger.build_why_it_matters(c)
    assert out.startswith("Short intext")


def test_why_falls_back_to_study_type_and_species():
    c = _cite(title="Canine parvovirus review")
    c.study_type = "Review"
    c.species_relevance = "Dogs"
    out = evidence_tagger.build_why_it_matters(c)
    assert "review" in out.lower()
    assert "dogs" in out.lower()


def test_why_respects_length_cap():
    long_text = "Extended intext passage. " * 40
    c = _cite(intext=long_text)
    out = evidence_tagger.build_why_it_matters(c)
    assert len(out) <= 180


# ─── enrich() end-to-end ──────────────────────────────────────────────────────

def test_enrich_populates_all_fields():
    citations = [
        _cite(
            title="Randomised controlled trial of meloxicam in cats",
            relevance="high",
            intext="Meloxicam reduced pain scores in cats [1].",
        ),
    ]
    evidence_tagger.enrich(citations)
    c = citations[0]
    assert c.study_type == "RCT"
    assert c.species_relevance == "Cats"
    assert c.evidence_tier == "direct"
    assert c.why_it_matters  # non-empty


def test_counts_by_tier():
    citations = [_cite(relevance="high") for _ in range(3)]
    citations.append(_cite(title="Review of FIP", relevance="moderate"))
    evidence_tagger.enrich(citations)
    counts = evidence_tagger.counts_by_tier(citations)
    assert counts["direct"] == 3
    assert counts["review"] == 1
    assert counts["weak"] == 0
    assert counts["guideline"] == 0
