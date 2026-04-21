"""
Unit tests for app.services.evidence_tagger — pure logic, no I/O.

Covers the clinician-facing fields on each reference card:
  - study_type        (Review / RCT / Retrospective / Guideline / ...)
  - species_relevance (Dogs / Cats / Dogs & cats / ...)
  - relevance         (direct / related / background / tangential)   ← axis 1
  - strength          (guideline / systematic_review / clinical_study /
                       case_series / narrative_review / expert_consensus) ← axis 2
  - why_it_matters    (heuristic fallback — LLM overlay lives in why_it_matters.py)
"""
from app.models.chat import CitationItem
from app.services import evidence_tagger


def _cite(
    title: str = "",
    abstract: str = "",
    doc_type: str = "",
    rerank_score: float = 2.0,
    authors: str = "Smith et al.",
    journal: str = "JVIM",
    year: int = 2023,
    intext: str = "",
) -> CitationItem:
    return CitationItem(
        ref=1, title=title, journal=journal, year=year, doi="", url="",
        authors=authors, abstract=abstract, doc_type=doc_type,
        rerank_score=rerank_score, intext_passage=intext,
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


# ─── Axis 1: relevance (query-match) ─────────────────────────────────────────

def test_relevance_direct_on_strong_score_and_overlap():
    # High rerank score + at least one content-word overlap with query
    c = _cite(title="Feline lily nephrotoxicity management", rerank_score=2.0)
    assert evidence_tagger.classify_relevance(
        rerank_score=c.rerank_score, query="feline lily toxicosis", citation=c,
    ) == "direct"


def test_relevance_related_on_positive_score_low_overlap():
    c = _cite(title="Canine vaccine protocols", rerank_score=0.5)
    assert evidence_tagger.classify_relevance(
        rerank_score=c.rerank_score, query="feline lily toxicosis", citation=c,
    ) == "related"


def test_relevance_background_on_marginal_score():
    c = _cite(title="Generic veterinary overview", rerank_score=-0.5)
    out = evidence_tagger.classify_relevance(
        rerank_score=c.rerank_score, query="feline lily toxicosis", citation=c,
    )
    # Low score, no overlap → background
    assert out == "background"


def test_relevance_tangential_below_floor():
    c = _cite(title="Industrial polymer synthesis", rerank_score=-2.5)
    assert evidence_tagger.classify_relevance(
        rerank_score=c.rerank_score, query="feline lily toxicosis", citation=c,
    ) == "tangential"


# ─── Axis 2: strength (study-design) ─────────────────────────────────────────

def test_strength_guideline():
    c = _cite(title="ACVIM Consensus Statement on CKD")
    assert evidence_tagger.classify_strength(c) == "guideline"


def test_strength_systematic_review():
    c = _cite(title="Systematic review of NSAID toxicity in dogs")
    assert evidence_tagger.classify_strength(c) == "systematic_review"


def test_strength_rct_is_clinical_study():
    c = _cite(title="Randomised double-blind trial of meloxicam")
    assert evidence_tagger.classify_strength(c) == "clinical_study"


def test_strength_retrospective_is_clinical_study():
    c = _cite(title="Retrospective analysis of 112 cases")
    assert evidence_tagger.classify_strength(c) == "clinical_study"


def test_strength_case_series():
    c = _cite(title="A case series of 34 dogs with pericardial effusion")
    assert evidence_tagger.classify_strength(c) == "case_series"


def test_strength_narrative_review_default_for_review_keyword():
    c = _cite(title="Review of feline asthma")
    assert evidence_tagger.classify_strength(c) == "narrative_review"


def test_strength_falls_back_to_expert_consensus():
    c = _cite(title="Plasma lactate levels in septic dogs")
    # No design markers in title, doc_type empty → expert_consensus
    assert evidence_tagger.classify_strength(c) == "expert_consensus"


def test_strength_doc_type_article_maps_to_clinical_study():
    c = _cite(title="Plasma lactate levels", doc_type="ar")
    assert evidence_tagger.classify_strength(c) == "clinical_study"


# ─── why_it_matters (heuristic fallback) ─────────────────────────────────────

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


def test_why_falls_back_to_strength_and_species():
    c = _cite(title="Canine parvovirus review")
    c.strength = "narrative_review"
    c.species_relevance = "Dogs"
    out = evidence_tagger.build_why_it_matters(c)
    assert "narrative review" in out.lower()
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
            abstract="Double-blind RCT of meloxicam for osteoarthritis in cats.",
            rerank_score=2.0,
            intext="Meloxicam reduced pain scores in cats [1].",
        ),
    ]
    evidence_tagger.enrich(citations, query="meloxicam cats osteoarthritis")
    c = citations[0]
    assert c.study_type == "RCT"
    assert c.species_relevance == "Cats"
    assert c.strength == "clinical_study"
    assert c.relevance == "direct"
    assert c.why_it_matters  # non-empty


def test_counts_by_axes():
    # 3 direct/clinical_study, 1 related/narrative_review
    cs = [
        _cite(
            title=f"RCT of drug {i} in dogs",
            abstract="Randomised controlled trial in dogs.",
            rerank_score=2.0,
        )
        for i in range(3)
    ]
    cs.append(_cite(
        title="Review of FIP",
        abstract="Narrative review of feline infectious peritonitis.",
        rerank_score=-0.3,
    ))
    evidence_tagger.enrich(cs, query="dog rct")
    counts = evidence_tagger.counts_by_axes(cs)
    assert counts["relevance"]["direct"] == 3
    assert counts["strength"]["clinical_study"] == 3
    # FIP review: no overlap with "dog rct", score -0.3 → background
    assert counts["relevance"].get("background") == 1
    assert counts["strength"]["narrative_review"] == 1
