"""
Reliability & reference-UX integration tests for the chat pipeline.

Covers the new behaviours introduced for the graceful-failure / evidence-UX
upgrade:
  - weak retrieval → graceful consensus fallback (not a home-screen dump)
  - citation guard → consensus fallback with fallback_kind="guard_blocked"
  - follow-up fast path → delta-shaped answer & prior_citations reused
  - irrelevant reference suppression surfaces hidden_references
  - citation enrichment: study_type / species_relevance / evidence_tier / why_it_matters
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.live_search import LiveResource, SearchResult


# ─── Helpers (duplicated locally to keep this file standalone) ────────────────

def _parse_sse(response_text: str) -> list[dict]:
    events = []
    for line in response_text.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except Exception:
                pass
    return events


def _get_result(events: list[dict]) -> dict:
    for e in events:
        if e.get("type") == "result":
            return e["payload"]
    raise AssertionError("No result event in SSE stream")


def _fake_live(title: str, abstract: str, doi: str = "10.1/x") -> LiveResource:
    return LiveResource(
        source="ScienceDirect",
        title=title,
        journal="Veterinary Dermatology",
        year=2023,
        authors="Smith et al.",
        doi=doi,
        url=f"https://doi.org/{doi}",
        abstract=abstract,
    )


def _patch_search(resources=None, errors=None):
    return patch(
        "app.api.chat.search_live",
        return_value=SearchResult(resources=resources or [], errors=errors or []),
    )


def _patch_refine(value="search terms"):
    return patch("app.api.chat.ClaudeService.refine_query", return_value=value)


def _patch_stream(chunks):
    """Mock ClaudeService.stream to yield canned chunks."""
    return patch("app.api.chat.ClaudeService.stream", return_value=iter(chunks))


def _patch_generate_flow(value=None):
    return patch("app.api.chat.ClaudeService.generate_flow", return_value=value)


def _patch_consensus_fallback(text: str = "**Literature synthesis incomplete — consensus-based summary only.**\n\n## Safe Clinical Summary\n\n- Step 1 [Guideline/Consensus]\n- Step 2 [No direct evidence]\n\n## Monitoring & Escalation\n\n- Watch for X\n\n## What to Do Next\n\n- Retry with more context"):
    return patch("app.api.chat.generate_consensus_fallback", return_value=text)


def _passthrough_rerank_live(_query, resources, _top_k=5, _use_reranker=True):
    """Preserve manually-pinned rerank_score values in tests (default
    rerank_live overwrites to 0.0 when use_reranker=False)."""
    return resources


def _patch_rerank_live():
    return patch("app.api.chat.rerank_live", side_effect=_passthrough_rerank_live)


# ─── Weak / no retrieval → consensus fallback ────────────────────────────────

def test_no_retrieval_produces_consensus_fallback(test_client):
    """When retrieval is empty, the backend must NOT dump an error — it must
    generate a consensus fallback with fallback_kind='no_retrieval'."""
    with _patch_refine(), _patch_search([]), _patch_consensus_fallback():
        resp = test_client.post("/chat", json={"query": "obscure veterinary question"})
    assert resp.status_code == 200
    result = _get_result(_parse_sse(resp.text))

    assert result["fallback_kind"] == "no_retrieval"
    assert result["evidence_mode"] == "consensus"
    assert result["citations"] == []
    assert "Literature synthesis incomplete" in result["answer"]


def test_consensus_fallback_retrieval_quality_weak(test_client):
    with _patch_refine(), _patch_search([]), _patch_consensus_fallback():
        resp = test_client.post("/chat", json={"query": "obscure veterinary question"})
    result = _get_result(_parse_sse(resp.text))
    assert result["retrieval_quality"] == "weak"


def test_consensus_fallback_exception_still_returns_safe_text(test_client):
    """If the consensus fallback Claude call fails, the stream must still
    return a safe human-readable message — not a 500 or a raw exception."""
    with _patch_refine(), _patch_search([]), \
         patch("app.api.chat.generate_consensus_fallback", side_effect=RuntimeError("boom")):
        resp = test_client.post("/chat", json={"query": "x"})
    result = _get_result(_parse_sse(resp.text))
    assert result["fallback_kind"] == "no_retrieval"
    assert "Literature synthesis incomplete" in result["answer"]


# ─── Citation guard ───────────────────────────────────────────────────────────

def test_citation_guard_triggers_consensus_fallback(test_client):
    """A structured answer with zero trust tags must be replaced by the
    consensus fallback (not by a 'try again' one-liner)."""
    structured_but_uncited = (
        "## Immediate Priorities\n\n"
        "- Do X\n- Do Y\n\n"
        "## Clinical Frame\n\n"
        "Some frame without any trust tag at all."
    )
    with _patch_refine(), \
         _patch_search([_fake_live("T", "A")]), \
         _patch_stream([structured_but_uncited]), \
         _patch_generate_flow(), \
         _patch_consensus_fallback():
        resp = test_client.post("/chat", json={"query": "canine pyoderma"})
    result = _get_result(_parse_sse(resp.text))
    assert result["fallback_kind"] == "guard_blocked"
    assert result["evidence_mode"] == "consensus"


def test_trust_tag_present_bypasses_guard(test_client):
    """A structured answer with at least one [Guideline/Consensus] must pass the guard."""
    structured_tagged = (
        "## Immediate Priorities\n\n"
        "- Do X [Guideline/Consensus]\n"
        "- Do Y [Consensus]\n"
    )
    with _patch_refine(), \
         _patch_search([_fake_live("T", "A")]), \
         _patch_stream([structured_tagged]), \
         _patch_generate_flow():
        resp = test_client.post("/chat", json={"query": "canine pyoderma"})
    result = _get_result(_parse_sse(resp.text))
    assert result["fallback_kind"] is None
    # Not literature — there were no [N] cites, just consensus
    assert result["evidence_mode"] == "consensus"


# ─── Reference suppression → hidden_references ────────────────────────────────

def test_uncited_moderate_refs_are_hidden_from_main_panel(test_client):
    """Moderate-relevance references that Claude didn't cite must move from
    the main panel to the 'Retrieved but not used' collapsible (hidden_references)."""
    answer = (
        "## Direct Evidence\n\n"
        "- Fact A [1] [Direct evidence]\n\n"
        "## Standard-of-Care Guidance\n\n"
        "- Fact B [Guideline/Consensus]\n"
    )
    # Two live resources: one will be cited [1], the other is uncited + moderate
    resources = [
        _fake_live("Cited study", "Directly supports fact A.", doi="10.1/a"),
        _fake_live("Uncited tangential", "Tangential abstract.", doi="10.1/b"),
    ]
    # Manually pin rerank_score on the resources so hygiene filter has
    # something deterministic to work with. First is high, second moderate.
    resources[0].rerank_score = 4.0
    resources[1].rerank_score = 0.5
    with _patch_refine(), _patch_search(resources), _patch_rerank_live(), \
         _patch_stream([answer]), _patch_generate_flow():
        resp = test_client.post("/chat", json={"query": "canine atopic dermatitis"})
    result = _get_result(_parse_sse(resp.text))
    # The cited source [1] must be in the main panel.
    main_refs = [c["ref"] for c in result["citations"]]
    assert 1 in main_refs
    # The uncited moderate one must appear in hidden_references.
    hidden_titles = [h["title"] for h in result.get("hidden_references", [])]
    assert "Uncited tangential" in hidden_titles


# ─── Evidence enrichment — reference-card fields ──────────────────────────────

def test_citations_are_enriched_with_clinician_fields(test_client):
    """Every citation must carry study_type / species_relevance / evidence_tier /
    why_it_matters so the reference card UX has the data it needs."""
    answer = "## Direct Evidence\n\n- Finding [1] [Direct evidence]\n"
    resources = [
        _fake_live(
            "Randomised controlled trial of amoxicillin in dogs",
            "Background: dogs with pyoderma. Methods: double-blind RCT.",
            doi="10.1/q",
        ),
    ]
    resources[0].rerank_score = 4.0
    with _patch_refine(), _patch_search(resources), _patch_rerank_live(), \
         _patch_stream([answer]), _patch_generate_flow():
        resp = test_client.post("/chat", json={"query": "canine pyoderma"})
    result = _get_result(_parse_sse(resp.text))
    c = result["citations"][0]
    assert c["study_type"] == "RCT"
    assert c["species_relevance"] == "Dogs"
    assert c["evidence_tier"] == "direct"
    assert c["why_it_matters"]  # non-empty


def test_evidence_counts_included_in_response(test_client):
    """The response must carry the evidence_counts dict used by the UI strip."""
    answer = "## Direct Evidence\n\n- Finding [1] [Direct evidence]\n"
    resources = [_fake_live("RCT in dogs", "RCT abstract.")]
    resources[0].rerank_score = 4.0
    with _patch_refine(), _patch_search(resources), _patch_rerank_live(), \
         _patch_stream([answer]), _patch_generate_flow():
        resp = test_client.post("/chat", json={"query": "canine pyoderma"})
    result = _get_result(_parse_sse(resp.text))
    assert "evidence_counts" in result
    assert result["evidence_counts"]["direct"] >= 1


# ─── Follow-up fast path → delta-shaped answer ────────────────────────────────

def test_follow_up_reuses_prior_citations_and_skips_retrieval(test_client):
    """When prior_citations + history are supplied, retrieval must be skipped
    entirely and the response must be produced from the reused citations."""
    delta_answer = (
        "## What Changed\n\n- Patient now PU/PD [1]\n\n"
        "## What Changes in Management Now\n\n- Adjust fluids [Guideline/Consensus]\n"
    )
    prior_citations = [{
        "ref": 1,
        "title": "Parenchymal kidney disease in dogs",
        "journal": "JVIM", "year": 2020,
        "doi": "10.1/old", "url": "https://doi.org/10.1/old",
        "authors": "Prior Author",
        "abstract": "An earlier study.",
        "relevance": "high",
    }]
    # If retrieval fires, the test fails — patch search_live to explode.
    with _patch_refine(), \
         patch("app.api.chat.search_live", side_effect=AssertionError("retrieval must be skipped")), \
         _patch_stream([delta_answer]), \
         _patch_generate_flow():
        resp = test_client.post("/chat", json={
            "query": "patient is now PU/PD",
            "history": [
                {"role": "user", "content": "initial question"},
                {"role": "assistant", "content": "initial answer [1]"},
            ],
            "prior_citations": prior_citations,
        })
    result = _get_result(_parse_sse(resp.text))
    assert "## What Changed" in result["answer"]
    assert result["fallback_kind"] is None


# ─── Emergency success path still works end-to-end ────────────────────────────

def test_emergency_query_sends_preliminary_event(test_client):
    """Regression guard — emergency preliminary card must still fire
    instantly before the LLM call."""
    resp = test_client.post("/chat", json={"query": "my dog ate xylitol"})
    events = _parse_sse(resp.text)
    kinds = [e.get("type") for e in events]
    assert "emergency_preliminary" in kinds
