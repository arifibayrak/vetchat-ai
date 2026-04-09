import asyncio
import json
import logging
import re
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.auth import get_optional_user
from app.config import get_settings
from app.models.chat import ChatRequest
from app.services import citation_builder, disclaimer_injector
from app.services.claude_service import ClaudeService
from app.services.emergency_detector import DISCLAIMER, get_detector
from app.services.live_search import search_live

_log = logging.getLogger(__name__)
router = APIRouter()

_STOP_WORDS = {
    "the","a","an","and","or","in","of","to","for","with","at","by","from",
    "is","are","was","were","that","this","it","as","on","be","been","has",
    "have","had","not","but","its","which","may","also","been","be","we",
}


def _extract_intext_passage(answer: str, ref_num: int) -> str:
    """Extract the exact sentence(s) from the answer that cite [ref_num]."""
    # Match full sentence(s) containing the citation marker
    pattern = rf"[^.!?\n]*\[{ref_num}\][^.!?\n]*[.!?]"
    matches = re.findall(pattern, answer)
    if not matches:
        return ""
    # Clean up markdown artifacts (bold markers, leading bullets/spaces)
    cleaned = " ".join(m.strip().lstrip("▸•- ").replace("**", "") for m in matches)
    return cleaned


def _extract_relevant_quote(answer: str, ref_num: int, abstract: str) -> str:
    """
    Find 1-3 consecutive abstract sentences most relevant to the claim citing [ref_num].
    Returns a passage (not just one sentence) for richer context.
    """
    if not abstract:
        return ""
    pattern = rf"[^.!?\n]*\[{ref_num}\][^.!?\n]*[.!?]"
    claim_matches = re.findall(pattern, answer)
    if not claim_matches:
        return ""
    claim_text = " ".join(claim_matches)
    claim_words = set(re.sub(r"[^\w\s]", "", claim_text.lower()).split()) - _STOP_WORDS

    sentences = re.split(r"(?<=[.!?])\s+", abstract.strip())
    if not sentences:
        return ""

    # Score each sentence
    scores = []
    for sent in sentences:
        sent_words = set(re.sub(r"[^\w\s]", "", sent.lower()).split()) - _STOP_WORDS
        scores.append(len(claim_words & sent_words))

    best_idx = max(range(len(scores)), key=lambda i: scores[i])
    if scores[best_idx] < 2:
        return ""

    # Include the sentence before and after the best match for context
    start = max(0, best_idx - 1)
    end = min(len(sentences), best_idx + 2)
    passage = " ".join(sentences[start:end]).strip()
    return passage


def _event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _save_conversation(user_id: str, query: str, result: dict) -> None:
    """Persist a Q&A pair to the database. Silently skips if DB is not configured."""
    from app import database
    if database.SessionLocal is None:
        return
    from sqlalchemy import insert
    from app.models.db import conversations, messages

    conv_id = str(uuid.uuid4())
    try:
        async with database.SessionLocal() as session:
            await session.execute(
                insert(conversations).values(
                    id=conv_id,
                    user_id=user_id,
                    title=query[:60],
                )
            )
            await session.execute(
                insert(messages).values(
                    id=str(uuid.uuid4()),
                    conversation_id=conv_id,
                    role="user",
                    content=query,
                )
            )
            await session.execute(
                insert(messages).values(
                    id=str(uuid.uuid4()),
                    conversation_id=conv_id,
                    role="assistant",
                    content=result.get("answer", ""),
                    citations=result.get("citations"),
                    live_resources=result.get("live_resources"),
                    emergency=result.get("emergency", False),
                    resources=result.get("resources"),
                )
            )
            await session.commit()
    except Exception as exc:
        _log.warning("Failed to save conversation: %s", exc)


async def _chat_stream(
    query: str,
    user_id: str | None = None,
) -> AsyncGenerator[str, None]:
    settings = get_settings()

    # ── Step 1: Emergency detection (non-blocking — continues to full search) ──
    detector = get_detector()
    emergency = detector.check(query)
    emergency_resources = emergency.resources if emergency.is_emergency else []

    claude = ClaudeService(api_key=settings.anthropic_api_key, model=settings.claude_model)
    loop = asyncio.get_running_loop()

    # ── Step 2: Claude refines the user query into search terms ───────────────
    yield _event({"type": "progress", "step": 1, "label": "Understanding your question…", "icon": "🧠"})
    search_query = await loop.run_in_executor(None, claude.refine_query, query)

    # ── Step 3: Live API search — 3 per source ────────────────────────────────
    sources_label = " & ".join(
        s for s, key in [
            ("ScienceDirect", settings.sciencedirect_api_key),
            ("Springer Nature", settings.springer_nature_api_key),
        ] if key
    ) or "academic databases"

    yield _event({
        "type": "progress", "step": 2,
        "label": f'Searching {sources_label} for "{search_query}"…',
        "icon": "🔍",
    })

    search_result = await loop.run_in_executor(None, search_live, search_query, settings, 3)
    live_results = search_result.resources
    api_errors   = search_result.errors

    # ── No results — report and stop ──────────────────────────────────────────
    if not live_results:
        error_hint = f" ({api_errors[0]})" if api_errors else ""
        payload = {
            "answer": (
                f"I searched for **\"{search_query}\"** but could not retrieve papers "
                f"from the academic databases{error_hint}.\n\n"
                "Please verify your API keys in the `.env` file and try again:\n"
                "- **ScienceDirect:** https://dev.elsevier.com\n"
                "- **Springer Nature:** https://dev.springernature.com"
            ),
            "citations": [],
            "live_resources": [],
            "emergency": False,
            "resources": [],
            "disclaimer": DISCLAIMER,
            "search_query": search_query,
        }
        yield _event({"type": "result", "payload": payload})
        if user_id:
            await _save_conversation(user_id, query, payload)
        return

    yield _event({
        "type": "progress", "step": 3,
        "label": f"Found {len(live_results)} paper{'s' if len(live_results) != 1 else ''}. Analysing…",
        "icon": "📄",
    })

    context_block, citations = citation_builder.build_from_live(live_results)

    # ── Step 4: Claude generates the answer ───────────────────────────────────
    yield _event({"type": "progress", "step": 4, "label": "Generating evidence-based answer…", "icon": "🤖"})
    answer_raw = await loop.run_in_executor(
        None, claude.complete, query, context_block, settings.claude_max_tokens
    )
    answer = disclaimer_injector.inject(answer_raw)

    # Populate intext_passage and relevant_quote for each citation
    for c in citations:
        c.intext_passage = _extract_intext_passage(answer, c.ref)
        c.relevant_quote = _extract_relevant_quote(answer, c.ref, c.abstract)

    yield _event({"type": "progress", "step": 5, "label": "Formatting answer…", "icon": "✍️"})

    # ── Step 5: Final result ──────────────────────────────────────────────────
    payload = {
        "answer": answer,
        "citations": [c.model_dump() for c in citations],
        "live_resources": [
            {
                "source":   r.source,
                "title":    r.title,
                "journal":  r.journal,
                "year":     r.year,
                "authors":  r.authors,
                "doi":      r.doi,
                "url":      r.url,
                "abstract": r.abstract,
                "volume":   r.volume,
                "issue":    r.issue,
                "pages":    r.pages,
                "doc_type": r.doc_type,
                "cited_by": r.cited_by,
            }
            for r in live_results
        ],
        "emergency": emergency.is_emergency,
        "resources": emergency_resources,
        "disclaimer": DISCLAIMER,
        "search_query": search_query,
    }
    yield _event({"type": "result", "payload": payload})
    if user_id:
        await _save_conversation(user_id, query, payload)


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    current_user = get_optional_user(request)
    user_id = current_user["sub"] if current_user else None

    return StreamingResponse(
        _chat_stream(body.query.strip(), user_id=user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
