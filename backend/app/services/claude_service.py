"""
Claude API wrapper — streaming and non-streaming answers with citation context.
"""
import json
from pathlib import Path

import anthropic

from app.services.emergency_detector import DISCLAIMER

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "data" / "system_prompt.txt"

_FLOW_KEYWORDS = frozenset({
    "workup", "approach", "protocol", "algorithm", "diagnostic",
    "management", "treatment", "emergency", "differential", "triage",
    "assessment", "evaluation", "step", "procedure", "how to",
})

_FLOW_SYSTEM = (
    "You are a veterinary clinical decision support tool. "
    "Given a query and a clinical answer, produce a structured step-by-step clinical algorithm as JSON. "
    "Output ONLY valid JSON — no markdown fences, no explanation. "
    'Format: {"title": "Short title", "icon": "one emoji", "steps": [...], "source": "Reference if known"}\n'
    "Step types:\n"
    '- {"type": "node", "text": "≤8 words", "sub": "optional detail ≤12 words", "highlight": true/false}\n'
    '- {"type": "branch", "items": ["Option A", "Option B", "Option C"]}\n'
    '- {"type": "note", "text": "Clinical pearl or conditional step"}\n'
    "Rules: first node must have highlight:true (presenting problem). 6-12 steps total. "
    "Use branch for differential/classification splits. Use note for conditionals. "
    "source = main textbook or journal referenced."
)


def is_diagnostic_query(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _FLOW_KEYWORDS)
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

    def complete(self, query: str, context_block: str, max_tokens: int = 4096) -> str:
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

    def generate_flow(self, query: str, answer: str) -> dict | None:
        """
        Generate a structured clinical decision flow for diagnostic/algorithm queries.
        Returns a dict with title, icon, steps, source — or None on failure.
        """
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=800,
                system=_FLOW_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": f"Query: {query}\n\nAnswer:\n{answer[:2000]}",
                }],
            )
            text = response.content[0].text.strip()
            # Strip markdown fences if Claude adds them anyway
            if text.startswith("```"):
                parts = text.split("```")
                text = parts[1].lstrip("json").strip() if len(parts) > 1 else text
            return json.loads(text)
        except Exception:
            return None

    def stream(self, query: str, context_block: str, max_tokens: int = 4096):
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
        f"Instructions:\n"
        f"- Answer using the retrieved literature above. Cite every factual claim with [N] notation.\n"
        f"- If a source is a journal directory entry (no article text), you may mention the journal name "
        f"and URL as a resource the vet can consult, and cite it with [N].\n"
        f"- Do not make clinical claims that are not supported by the retrieved sources.\n"
        f"- If the retrieved content is insufficient to answer, say so clearly and suggest the vet "
        f"consult the listed journals directly."
    )
