"""
Claude API wrapper — streaming and non-streaming answers with citation context.
"""
import json
from pathlib import Path

import anthropic

from app.services.emergency_detector import DISCLAIMER

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "data" / "system_prompt.txt"

_FLOW_SYSTEM = (
    "You are a veterinary clinical decision support tool. "
    "Given a query and a clinical answer, decide whether a structured clinical algorithm card adds real value.\n\n"
    "Return the literal string null (no quotes, no JSON wrapper) if the query is:\n"
    "- A simple factual or yes/no question (e.g. 'Is X toxic to cats?', 'What is the half-life of Y?')\n"
    "- A single-concept knowledge question with a direct answer\n"
    "- A question where a sequential flow would be redundant or forced\n\n"
    "Return a JSON algorithm ONLY when there is a genuine multi-step clinical process to illustrate — "
    "e.g. a diagnostic workup, treatment protocol, triage algorithm, anaesthesia plan, or monitoring pathway.\n\n"
    "Output ONLY valid JSON or the literal null — no markdown fences, no explanation.\n"
    'JSON format: {"title": "Short title", "icon": "one emoji", "steps": [...], "source": "Reference if known"}\n'
    "Step types:\n"
    '- {"type": "node", "text": "≤8 words", "sub": "optional detail ≤12 words", "highlight": true/false}\n'
    '- {"type": "branch", "items": ["Option A", "Option B", "Option C"]}\n'
    '- {"type": "note", "text": "Clinical pearl or conditional step"}\n'
    "Rules: first node must have highlight:true (presenting problem). 6-12 steps total. "
    "Use branch for differential/classification splits. Use note for conditionals. "
    "source = main textbook or journal referenced."
)


def is_diagnostic_query(_query: str) -> bool:
    return True  # Claude decides — _FLOW_SYSTEM instructs it to return null when no flow is warranted
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

    def complete(
        self,
        query: str,
        context_block: str,
        max_tokens: int = 4096,
        history: list | None = None,
    ) -> str:
        """
        Non-streaming completion.
        Returns the full answer text (without disclaimer — caller adds that).
        When history is provided, Claude sees a proper multi-turn conversation.
        """
        user_message = _build_user_message(query, context_block, has_history=bool(history))
        messages = _build_messages(user_message, history)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=_cached_system(_load_system_prompt()),
            messages=messages,
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
                system=_cached_system(_FLOW_SYSTEM),
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

    def stream(
        self,
        query: str,
        context_block: str,
        max_tokens: int = 4096,
        history: list | None = None,
    ):
        """
        Streaming completion — yields text chunks.
        Caller is responsible for injecting disclaimer after the stream ends.
        """
        user_message = _build_user_message(query, context_block, has_history=bool(history))
        messages = _build_messages(user_message, history)
        with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            system=_cached_system(_load_system_prompt()),
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text


_MAX_ASSISTANT_CHARS = 1500


def _cached_system(prompt_text: str) -> list[dict]:
    """
    Wrap a system prompt with ephemeral cache_control so Claude can reuse
    the processed prompt across requests within ~5 min. Cuts latency on
    repeat calls (same system prompt is reloaded from cache, not reprocessed).
    """
    return [{
        "type": "text",
        "text": prompt_text,
        "cache_control": {"type": "ephemeral"},
    }]


def _truncate_assistant(text: str) -> str:
    """Keep assistant turns small so history doesn't blow the token budget."""
    if len(text) <= _MAX_ASSISTANT_CHARS:
        return text
    head = _MAX_ASSISTANT_CHARS // 2
    tail = _MAX_ASSISTANT_CHARS - head - 20  # 20 chars for elision marker
    return f"{text[:head]}\n\n…[prior answer truncated]…\n\n{text[-tail:]}"


def _build_messages(current_user_message: str, history: list | None) -> list[dict]:
    """
    Assemble the Claude messages array.
    history: list of ChatTurn (pydantic) or dicts with role + content.
    Empty/None → single-turn (identical to prior behavior).
    """
    messages: list[dict] = []
    for turn in history or []:
        if isinstance(turn, dict):
            role = turn.get("role")
            content = turn.get("content", "")
        else:
            role = getattr(turn, "role", None)
            content = getattr(turn, "content", "") or ""
        if role not in ("user", "assistant") or not content:
            continue
        if role == "assistant":
            content = _truncate_assistant(content)
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": current_user_message})
    return messages


def _build_user_message(query: str, context_block: str, has_history: bool = False) -> str:
    followup_note = (
        "\n- This is a FOLLOW-UP in an ongoing case. Produce a DELTA, not a re-statement. "
        "Use the FOLLOW-UP MODE sections exactly as defined in the system prompt "
        "(What Changed / What Changes in Management Now / What Stays the Same / "
        "Monitoring for the Next Interval / Escalation / Referral Triggers / "
        "Evidence Quality Note). Do NOT repeat the initial plan. Target 150-350 words.\n"
        if has_history else ""
    )
    return (
        f"{query}\n\n"
        f"## Retrieved Veterinary Literature\n"
        f"{context_block}\n\n"
        f"Instructions:\n"
        f"- Tag every factual claim using the evidence-tag system from the prompt "
        f"([N] / [Direct evidence] / [Review] / [Guideline/Consensus] / [Weak indirect] / "
        f"[No direct evidence] / [Gap]). Prefer [N] when a retrieved source supports the claim.\n"
        f"- Do not cite a [N] number that is not present in the Retrieved Literature block.\n"
        f"- If retrieved evidence is thin, lean on [Guideline/Consensus] — do not fabricate [N].\n"
        f"- Journal directory entries (title/URL only, no article text) may be cited as a resource "
        f"the vet can consult, but do not present them as directly supporting a clinical claim.\n"
        f"- Omit the References section entirely if nothing was cited with [N] — the UI handles the reference panel."
        f"{followup_note}"
    )
