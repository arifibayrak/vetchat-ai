"""
Claude API wrapper — streaming and non-streaming answers with citation context.
"""
from pathlib import Path

import anthropic

from app.services.emergency_detector import DISCLAIMER

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "data" / "system_prompt.txt"
_system_prompt: str | None = None


def _load_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return _system_prompt


def reload_system_prompt() -> None:
    """Force reload from disk — call after editing system_prompt.txt."""
    global _system_prompt
    _system_prompt = None


class ConfigurationError(Exception):
    pass


class ClaudeService:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        if not api_key:
            raise ConfigurationError(
                "ANTHROPIC_API_KEY is not set. Cannot initialise ClaudeService."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def refine_query(self, user_query: str) -> str:
        """
        Convert a natural language veterinary question into optimised academic search terms.
        Returns a concise query string (≤8 words) ready for ScienceDirect / Springer Nature.
        """
        response = self._client.messages.create(
            model=self._model,
            max_tokens=60,
            system=(
                "You are a veterinary research librarian. "
                "Convert the user's question into a concise academic search query "
                "for veterinary literature databases (ScienceDirect, Springer Nature). "
                "Output ONLY the search query — no explanation, no punctuation at the end. "
                "Use scientific/medical terminology. Include the animal species if mentioned. "
                "Maximum 8 words."
            ),
            messages=[{"role": "user", "content": user_query}],
        )
        return response.content[0].text.strip()

    def complete(self, query: str, context_block: str, max_tokens: int = 1024) -> str:
        """
        Non-streaming completion.
        Returns the full answer text (without disclaimer — caller adds that).
        """
        user_message = _build_user_message(query, context_block)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=_load_system_prompt(),
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def stream(self, query: str, context_block: str, max_tokens: int = 1024):
        """
        Streaming completion — yields text chunks.
        Caller is responsible for injecting disclaimer after the stream ends.
        """
        user_message = _build_user_message(query, context_block)
        with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            system=_load_system_prompt(),
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text


def _build_user_message(query: str, context_block: str) -> str:
    return (
        f"{query}\n\n"
        f"## Retrieved Veterinary Literature\n"
        f"{context_block}\n\n"
        f"Please answer based solely on the literature above. "
        f"Cite sources inline using [N] notation."
    )
