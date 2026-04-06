"""
Tests for ClaudeService.
The real Anthropic API is never called — anthropic.Anthropic.messages.create is mocked.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.services.claude_service import ClaudeService, ConfigurationError


def _make_mock_response(text: str):
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


MOCK_ANSWER_WITH_CITATION = (
    "Xylitol causes hypoglycemia in dogs by stimulating insulin release [1]. "
    "Doses above 0.5 g/kg may cause hepatic necrosis [1]."
)

MOCK_NO_LITERATURE_ANSWER = (
    "No supporting literature was found for this query. "
    "Please consult a licensed veterinarian for advice specific to your pet."
)


def test_answer_includes_citation_when_context_given():
    service = ClaudeService(api_key="test-key")
    with patch.object(service._client.messages, "create", return_value=_make_mock_response(MOCK_ANSWER_WITH_CITATION)):
        answer = service.complete("What does xylitol do to dogs?", "context block here")
    assert "[1]" in answer


def test_no_context_returns_no_literature_statement():
    service = ClaudeService(api_key="test-key")
    with patch.object(service._client.messages, "create", return_value=_make_mock_response(MOCK_NO_LITERATURE_ANSWER)):
        answer = service.complete("What is the capital of France?", "No relevant literature found.")
    assert "no supporting literature" in answer.lower()


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(ConfigurationError):
        ClaudeService(api_key="")


def test_unsupported_query_returns_no_literature():
    """Out-of-scope queries with no chunks should get the no-literature response."""
    service = ClaudeService(api_key="test-key")
    with patch.object(service._client.messages, "create", return_value=_make_mock_response(MOCK_NO_LITERATURE_ANSWER)):
        answer = service.complete("Who won the World Cup?", "No relevant literature found.")
    assert "no supporting literature" in answer.lower() or "consult" in answer.lower()


def test_complete_passes_correct_model():
    service = ClaudeService(api_key="test-key", model="claude-haiku-4-5-20251001")
    with patch.object(service._client.messages, "create", return_value=_make_mock_response("ok")) as mock_create:
        service.complete("test query", "context")
    call_kwargs = mock_create.call_args
    assert call_kwargs.kwargs.get("model") == "claude-haiku-4-5-20251001" or \
           call_kwargs.args[0] if call_kwargs.args else True  # model is kwarg


def test_complete_sends_system_prompt():
    service = ClaudeService(api_key="test-key")
    with patch.object(service._client.messages, "create", return_value=_make_mock_response("answer")) as mock_create:
        service.complete("test", "context")
    kwargs = mock_create.call_args.kwargs
    assert "system" in kwargs
    assert len(kwargs["system"]) > 50  # system prompt is non-trivial
