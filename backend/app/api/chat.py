import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.models.chat import ChatRequest
from app.services import citation_builder, disclaimer_injector
from app.services.claude_service import ClaudeService
from app.services.emergency_detector import DISCLAIMER, get_detector
from app.services.live_search import search_live

router = APIRouter()


def _event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _chat_stream(query: str) -> AsyncGenerator[str, None]:
    settings = get_settings()

    # ── Step 1: Emergency detection ───────────────────────────────────────────
    detector = get_detector()
    emergency = detector.check(query)
    if emergency.is_emergency:
        yield _event({
            "type": "result",
            "payload": {
                "answer": emergency.message,
                "citations": [],
                "live_resources": [],
                "emergency": True,
                "category": emergency.category,
                "matched_term": emergency.matched_term,
                "resources": emergency.resources,
                "disclaimer": DISCLAIMER,
            }
        })
        return

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
        yield _event({
            "type": "result",
            "payload": {
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
        })
        return

    yield _event({
        "type": "progress", "step": 3,
        "label": f"Found {len(live_results)} paper{'s' if len(live_results) != 1 else ''}. Analysing…",
        "icon": "📄",
    })

    context_block, citations = citation_builder.build_from_live(live_results)

    # ── Step 4: Claude generates the answer ───────────────────────────────────
    yield _event({"type": "progress", "step": 4, "label": "Asking Claude AI…", "icon": "🤖"})
    answer_raw = await loop.run_in_executor(None, claude.complete, query, context_block)
    answer = disclaimer_injector.inject(answer_raw)

    yield _event({"type": "progress", "step": 5, "label": "Formatting answer…", "icon": "✍️"})

    # ── Step 5: Final result ──────────────────────────────────────────────────
    yield _event({
        "type": "result",
        "payload": {
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
                }
                for r in live_results
            ],
            "emergency": False,
            "resources": [],
            "disclaimer": DISCLAIMER,
            "search_query": search_query,
        }
    })


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _chat_stream(body.query.strip()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
