import asyncio
import json
import logging
import re
import uuid
from typing import AsyncGenerator

import chromadb
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.auth import get_optional_user
from app.config import get_settings
from app.models.chat import ChatRequest
from app.services import citation_builder, disclaimer_injector
from app.services.claude_service import ClaudeService, is_diagnostic_query
from app.services.emergency_detector import DISCLAIMER, get_detector
from app.services.live_search import search_live
from app.services.retriever import search as chroma_search
from app.services.reranker import rerank

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


_CITATION_PATTERN = re.compile(r"\[\d+\]")

# Response served when the model generates an answer but cites nothing —
# this is a trust boundary: we never ship an uncited clinical answer.
_NO_CITATION_ANSWER = (
    "I was unable to find peer-reviewed research that directly addresses your question "
    "in the retrieved literature. Please try rephrasing your question or ask about a "
    "related veterinary topic."
)


async def _chat_stream(
    query: str,
    chroma_collection: chromadb.Collection | None = None,
    user_id: str | None = None,
) -> AsyncGenerator[str, None]:
    settings = get_settings()

    # ── Step 1: Emergency detection ───────────────────────────────────────────
    detector = get_detector()
    emergency = detector.check(query)
    emergency_resources = emergency.resources if emergency.is_emergency else []

    claude = ClaudeService(api_key=settings.anthropic_api_key, model=settings.claude_model)
    loop = asyncio.get_running_loop()

    # ── Step 2: Refine query for academic search ──────────────────────────────
    yield _event({"type": "progress", "step": 1, "label": "Understanding your question…", "icon": "🧠"})
    search_query = await loop.run_in_executor(None, claude.refine_query, query)

    # ── Step 3: Live API search + ChromaDB vector search (parallel) ───────────
    live_sources = " & ".join(
        s for s, key in [
            ("ScienceDirect", settings.sciencedirect_api_key),
            ("Springer Nature", settings.springer_nature_api_key),
        ] if key
    )
    all_sources_label = ", ".join(filter(None, [live_sources or None, "Taylor & Francis journals"])) or "academic databases"

    yield _event({
        "type": "progress", "step": 2,
        "label": f'Searching {all_sources_label} for "{search_query}"…',
        "icon": "🔍",
    })

    # Run live API search and ChromaDB vector search concurrently
    live_task = loop.run_in_executor(None, search_live, search_query, settings, 3)

    chroma_chunks = []
    if chroma_collection is not None:
        chroma_raw = await loop.run_in_executor(
            None, chroma_search, search_query, chroma_collection,
            10, settings.embedding_model,
        )
        chroma_chunks = rerank(search_query, chroma_raw, top_k=5, use_reranker=settings.use_reranker)

    search_result = await live_task
    live_results = search_result.resources
    api_errors   = search_result.errors

    # ── No results from either source ─────────────────────────────────────────
    if not live_results and not chroma_chunks:
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

    total_sources = len(live_results) + len(chroma_chunks)
    yield _event({
        "type": "progress", "step": 3,
        "label": f"Found {total_sources} source{'s' if total_sources != 1 else ''}. Analysing evidence…",
        "icon": "📄",
    })

    # ── Build unified context block ────────────────────────────────────────────
    # Live results form the base; ChromaDB chunks (T&F + mock) are appended and deduplicated.
    if live_results:
        live_block, live_citations = citation_builder.build_from_live(live_results)
        context_block, citations = citation_builder.merge(live_citations, live_block, chroma_chunks)
    else:
        context_block, citations = citation_builder.build(chroma_chunks)

    # ── Step 4: Claude generates the answer ──────────────────────────────────
    yield _event({"type": "progress", "step": 4, "label": "Generating evidence-based answer…", "icon": "🤖"})
    answer_raw = await loop.run_in_executor(
        None, claude.complete, query, context_block, settings.claude_max_tokens
    )

    # ── Citation guard: never serve a clinically uncited answer ───────────────
    # If Claude produced no [N] markers the answer is not grounded in retrieved
    # sources — replace it with the standard "unable to find" message.
    if not _CITATION_PATTERN.search(answer_raw):
        _log.warning("Citation guard triggered for query: %s", query[:120])
        answer_raw = _NO_CITATION_ANSWER
        citations = []

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

    # ── Step 6: Optional clinical flow for diagnostic queries ─────────────────
    if is_diagnostic_query(query) and citations:
        flow_data = await loop.run_in_executor(None, claude.generate_flow, query, answer_raw)
        if flow_data:
            yield _event({"type": "flow", "payload": flow_data})


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    current_user = get_optional_user(request)
    user_id = current_user["sub"] if current_user else None

    # Pass the ChromaDB collection (holds T&F journals + mock data) into the stream
    chroma_collection = getattr(request.app.state, "chroma_collection", None)

    return StreamingResponse(
        _chat_stream(body.query.strip(), chroma_collection=chroma_collection, user_id=user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
