"""
Integration tests for POST /chat endpoint (SSE stream).
All Claude and live-search calls are mocked — no real API keys needed.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.live_search import LiveResource, SearchResult


# ─── Helpers ─────────────────────────────────────────────────────────────────

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


def _mock_live_resources(n: int = 3) -> list[LiveResource]:
    return [
        LiveResource(
            source="ScienceDirect" if i % 2 == 0 else "Springer Nature",
            title=f"Canine atopic dermatitis study {i}",
            journal="Veterinary Dermatology",
            year=2022 + i,
            authors=f"Author {i}",
            doi=f"10.1000/mock.{i}",
            url=f"https://doi.org/10.1000/mock.{i}",
            abstract=f"Abstract for study {i} about atopic dermatitis in dogs.",
        )
        for i in range(1, n + 1)
    ]


def _mock_search(resources=None, errors=None):
    """Patch search_live to return a canned SearchResult."""
    result = SearchResult(
        resources=resources if resources is not None else _mock_live_resources(),
        errors=errors or [],
    )
    return patch("app.api.chat.search_live", return_value=result)


def _mock_refine(query="canine atopic dermatitis pruritus"):
    return patch("app.api.chat.ClaudeService.refine_query", return_value=query)


def _mock_complete(answer_text: str):
    return patch("app.api.chat.ClaudeService.complete", return_value=answer_text)


MOCK_ANSWER = (
    "Canine atopic dermatitis is a common allergic skin disease [1]. "
    "Clinical signs include pruritus and erythema [2]. "
    "Always consult a veterinarian."
)

DISCLAIMER_FRAGMENT = "educational purposes only"


# ─── Emergency short-circuit ─────────────────────────────────────────────────

def test_emergency_short_circuits_llm(test_client):
    with patch("app.api.chat.ClaudeService.refine_query") as mock_refine, \
         patch("app.api.chat.ClaudeService.complete") as mock_complete:
        resp = test_client.post("/chat", json={"query": "my dog ate xylitol"})
    assert resp.status_code == 200
    result = _get_result(_parse_sse(resp.text))
    assert result["emergency"] is True
    mock_refine.assert_not_called()
    mock_complete.assert_not_called()


def test_emergency_response_shape(test_client):
    resp = test_client.post("/chat", json={"query": "dog is having a seizure"})
    result = _get_result(_parse_sse(resp.text))
    assert result["emergency"] is True
    assert isinstance(result["resources"], list)
    assert len(result["resources"]) > 0
    assert result["citations"] == []


def test_emergency_response_has_hotline(test_client):
    resp = test_client.post("/chat", json={"query": "cat ate grapes"})
    result = _get_result(_parse_sse(resp.text))
    hotlines = " ".join(result["resources"])
    assert "888" in hotlines or "855" in hotlines


# ─── Normal query ─────────────────────────────────────────────────────────────

def test_normal_query_returns_200_with_answer(test_client):
    with _mock_refine(), _mock_search(), _mock_complete(MOCK_ANSWER):
        resp = test_client.post("/chat", json={"query": "what causes itchy skin in dogs?"})
    assert resp.status_code == 200
    result = _get_result(_parse_sse(resp.text))
    assert result["emergency"] is False
    assert len(result["answer"]) > 10


def test_normal_query_has_citations(test_client):
    with _mock_refine(), _mock_search(), _mock_complete(MOCK_ANSWER):
        resp = test_client.post("/chat", json={"query": "canine atopic dermatitis causes"})
    result = _get_result(_parse_sse(resp.text))
    assert isinstance(result["citations"], list)
    assert len(result["citations"]) > 0


def test_normal_query_has_live_resources(test_client):
    with _mock_refine(), _mock_search(_mock_live_resources(3)), _mock_complete(MOCK_ANSWER):
        resp = test_client.post("/chat", json={"query": "feline asthma treatment"})
    result = _get_result(_parse_sse(resp.text))
    assert isinstance(result["live_resources"], list)
    assert len(result["live_resources"]) == 3


def test_search_query_included_in_result(test_client):
    with _mock_refine("canine atopic dermatitis pruritus"), _mock_search(), _mock_complete(MOCK_ANSWER):
        resp = test_client.post("/chat", json={"query": "why is my dog scratching?"})
    result = _get_result(_parse_sse(resp.text))
    assert result.get("search_query") == "canine atopic dermatitis pruritus"


def test_disclaimer_present_in_non_emergency_answer(test_client):
    with _mock_refine(), _mock_search(), _mock_complete(MOCK_ANSWER):
        resp = test_client.post("/chat", json={"query": "canine atopic dermatitis treatment"})
    result = _get_result(_parse_sse(resp.text))
    assert DISCLAIMER_FRAGMENT in result["answer"].lower()


# ─── Progress events ──────────────────────────────────────────────────────────

def test_progress_events_emitted(test_client):
    with _mock_refine(), _mock_search(), _mock_complete(MOCK_ANSWER):
        resp = test_client.post("/chat", json={"query": "dog skin allergy"})
    events = _parse_sse(resp.text)
    progress = [e for e in events if e.get("type") == "progress"]
    assert len(progress) >= 3, f"Expected at least 3 progress events, got {len(progress)}"


def test_result_event_is_last(test_client):
    with _mock_refine(), _mock_search(), _mock_complete(MOCK_ANSWER):
        resp = test_client.post("/chat", json={"query": "feline asthma"})
    events = _parse_sse(resp.text)
    assert events[-1]["type"] == "result"


# ─── No-results path ─────────────────────────────────────────────────────────

def test_no_api_results_returns_informative_message(test_client):
    with _mock_refine("canine pruritus"), \
         _mock_search(resources=[], errors=["ScienceDirect: 401 Unauthorized"]), \
         patch("app.api.chat.ClaudeService.complete") as mock_complete:
        resp = test_client.post("/chat", json={"query": "dog itching"})
    result = _get_result(_parse_sse(resp.text))
    mock_complete.assert_not_called()
    assert result["emergency"] is False
    assert result["citations"] == []
    # Should mention the search query and the error
    assert "canine pruritus" in result["answer"]


def test_no_results_path_does_not_call_claude_complete(test_client):
    with _mock_refine(), \
         _mock_search(resources=[], errors=[]), \
         patch("app.api.chat.ClaudeService.complete") as mock_complete:
        test_client.post("/chat", json={"query": "quantum physics"})
    mock_complete.assert_not_called()


# ─── Health ───────────────────────────────────────────────────────────────────

def test_health_endpoint(test_client):
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ─── Service-level ────────────────────────────────────────────────────────────

def test_missing_anthropic_key_raises_configuration_error():
    from app.services.claude_service import ClaudeService, ConfigurationError
    with pytest.raises(ConfigurationError):
        ClaudeService(api_key="")


def test_ingest_without_api_keys_returns_503(test_client):
    from app import config as cfg_module
    from app.config import Settings
    original = cfg_module._settings
    cfg_module._settings = Settings(
        anthropic_api_key="test-sk-fake-key-12345",
        sciencedirect_api_key="",
        springer_nature_api_key="",
    )
    try:
        resp = test_client.post("/ingest", json={"queries": ["veterinary toxicology"], "count": 5})
        assert resp.status_code == 503
        assert "error" in resp.json()
    finally:
        cfg_module._settings = original
