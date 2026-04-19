"""
Graceful fallback answers for when the normal literature-grounded pipeline
can't produce a full answer. Goal: never dump the user back to the home
screen — always return a short, safe, consensus-based clinical summary
with an explicit "literature synthesis incomplete" note.

Three fallback modes map to ChatResponse.fallback_kind:
  - "no_retrieval"   — retrieval returned zero papers
  - "guard_blocked"  — citation guard fired (structured answer with no cites)
  - "timeout_partial" — generation stalled / exceeded hard cap

All three are rendered with a distinctive 'fallback' shell on the frontend
that offers Retry / Continue / Expand-search actions.
"""
from __future__ import annotations

from app.services.claude_service import ClaudeService

_CONSENSUS_SYSTEM = (
    "You are Arlo, a veterinary clinical reference tool. The literature retrieval "
    "pipeline did NOT return directly relevant peer-reviewed sources for this query. "
    "Your job is to produce a short, SAFE consensus summary the vet can act on while "
    "we acknowledge the gap clearly.\n\n"
    "STRICT RULES:\n"
    "1. Be concise — 180-320 words MAX.\n"
    "2. Tag every factual claim with [Guideline/Consensus] or [No direct evidence].\n"
    "3. Do NOT fabricate [N] citations — there are no retrieved sources to number.\n"
    "4. Open with exactly this line: '**Literature synthesis incomplete — consensus-based summary only.**'\n"
    "5. Use exactly these three sections (in this order):\n"
    "   ## Safe Clinical Summary\n"
    "   3-5 short, action-oriented bullets covering: immediate priorities, most-likely frame, "
    "   standard-of-care actions. Tag each [Guideline/Consensus] or [No direct evidence].\n"
    "   ## Monitoring & Escalation\n"
    "   2-3 bullets naming concrete thresholds that change disposition.\n"
    "   ## What to Do Next\n"
    "   One bullet recommending the vet: retry with more specific clinical context, or "
    "   consult the listed veterinary textbooks / formularies directly.\n"
    "6. Do not invent doses you are not confident about; prefer ranges + 'confirm with formulary'.\n"
    "7. Do not write pathophysiology lectures. No background paragraphs.\n"
    "8. Never claim literature support. Your entire answer is consensus-based.\n"
)

_TIMEOUT_SYSTEM = (
    "You are Arlo, a veterinary clinical reference tool. Literature retrieval succeeded "
    "but synthesis was interrupted. Produce a short, safe consensus summary as a fallback.\n\n"
    "STRICT RULES:\n"
    "1. Be concise — 200-350 words MAX.\n"
    "2. Tag claims [N] when the retrieved source in the context block supports them; "
    "   otherwise tag [Guideline/Consensus] or [No direct evidence].\n"
    "3. Open with exactly: '**Partial answer — full synthesis was interrupted.**'\n"
    "4. Use these three sections: ## Safe Clinical Summary, ## Monitoring & Escalation, ## What to Do Next.\n"
    "5. Prefer safety-first guidance; do not invent doses.\n"
)


def generate_consensus_fallback(
    claude: ClaudeService,
    query: str,
    emergency_category: str | None = None,
) -> str:
    """Build a consensus-only fallback answer (no retrieval available)."""
    emergency_hint = (
        f"\n\nThis query triggered the emergency category: {emergency_category}. "
        f"Lead with immediate stabilisation actions tailored to this category."
        if emergency_category else ""
    )
    user_message = (
        f"Vet's question: {query}{emergency_hint}\n\n"
        "No peer-reviewed sources were retrieved. Produce the consensus-only "
        "fallback answer per the strict rules."
    )
    # Bypass the default system prompt — use the stricter fallback system.
    client = claude._client  # single private call into the wrapper
    response = client.messages.create(
        model=claude._model,
        max_tokens=900,
        system=_CONSENSUS_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def generate_partial_fallback(
    claude: ClaudeService,
    query: str,
    context_block: str,
    accumulated: str,
) -> str:
    """
    Produce a safe wrap-up when the main stream stalled. Used when the user
    has already seen partial content — we append a clear "what to do next"
    block so the answer is usable rather than truncated mid-sentence.
    """
    user_message = (
        f"Vet's question: {query}\n\n"
        f"Partial answer produced so far (do NOT repeat it verbatim — continue from here if needed):\n"
        f"{accumulated}\n\n"
        f"Retrieved literature (for citation if you add a safety-net closing):\n"
        f"{context_block[:3000]}\n\n"
        "Append ONLY a short safety-net closing: 2-3 bullets of immediate actions and a one-line "
        "evidence-quality note. Do not rewrite what's above. Output ≤150 words."
    )
    client = claude._client
    response = client.messages.create(
        model=claude._model,
        max_tokens=400,
        system=_TIMEOUT_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text
