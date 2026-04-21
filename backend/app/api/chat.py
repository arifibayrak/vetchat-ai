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
from app.services import citation_builder, disclaimer_injector, evidence_tagger, tox_intent
from app.services.claude_service import ClaudeService, is_diagnostic_query
from app.services.emergency_detector import DISCLAIMER, get_detector
from app.services.fallback_generator import (
    generate_consensus_fallback,
    generate_partial_fallback,
)
from app.services.live_search import search_live
from app.services.query_expander import expand as hyde_expand
from app.services.retriever import RetrievedChunk, search as chroma_search
from app.services.reranker import rerank, rerank_live
from app.services.species_filter import detect_species, filter_and_reorder
from app.services import why_it_matters as why_it_matters_service

_log = logging.getLogger(__name__)
router = APIRouter()

_STOP_WORDS = {
    "the","a","an","and","or","in","of","to","for","with","at","by","from",
    "is","are","was","were","that","this","it","as","on","be","been","has",
    "have","had","not","but","its","which","may","also","been","be","we",
}


def _extract_intext_passage(answer: str, ref_num: int) -> str:
    """
    Extract the per-claim sentence(s) from the answer body that cite [ref_num].

    Strips out:
      - The References section (post-"## References" or trailing "---" divider).
      - The PREAMBLE before the first section header (##) — that's where the
        "Limited Direct Evidence — Only sources [1], [2], [3], and [4] are
        directly relevant…" banner lives, and it matches every ref.
      - Summary sentences that cite 3+ distinct refs — those are guaranteed
        to be evidence-mix summaries, not per-claim statements.
    """
    body = answer

    # 1. Cut off the References section
    for marker_re in (r"\n##\s+References\s*\n", r"\n#\s+References\s*\n", r"\n##?\s+Works?\s+cited\s*\n"):
        m = re.search(marker_re, body, re.I)
        if m:
            body = body[: m.start()]
            break

    # 2. Skip the preamble — everything before the first section header.
    # This is where the "Limited Direct Evidence" banner typically sits.
    first_header = re.search(r"\n##\s+", body)
    if first_header:
        body = body[first_header.start():]

    # 3. Gather candidate sentences citing this ref
    pattern = rf"[^.!?\n]*\[{ref_num}\][^.!?\n]*[.!?]"
    matches = re.findall(pattern, body)
    if not matches:
        return ""

    # 4. Drop sentences that cite 3+ distinct refs — those are summary lines
    # ("Sources [1], [2], [3], and [4] document…") that leak the ugly
    # ", , , and" artefact once [N] markers are stripped downstream.
    claim_sentences = [
        m for m in matches
        if len(set(re.findall(r"\[(\d+)\]", m))) < 3
    ]
    if not claim_sentences:
        return ""

    cleaned = " ".join(s.strip().lstrip("▸•- ").replace("**", "") for s in claim_sentences)
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
# Any trust tag — [N], or any of the evidence-tier tags emitted by the
# tiered-trust system prompt. Guard fires only if NONE of these appear in
# a structured answer (i.e. Claude bypassed the trust model entirely).
_TRUST_TAG_PATTERN = re.compile(
    r"\[(?:"
    r"\d+"
    r"|Consensus"
    r"|Guideline/Consensus"
    r"|Direct evidence"
    r"|Review"
    r"|Weak indirect"
    r"|No direct evidence"
    r"|Gap"
    r")\]"
)
# Matches a structured clinical answer (has at least one ## section heading).
# Used to distinguish hallucinated clinical prose from a deliberate "I can't answer" response.
_STRUCTURED_ANSWER_PATTERN = re.compile(r"^##\s+\w", re.MULTILINE)

# Only served when Claude produces a fully structured clinical answer with zero citations —
# meaning it hallucinated without grounding in any retrieved source.
_NO_CITATION_ANSWER = (
    "I was unable to find peer-reviewed research that directly addresses your question "
    "in the retrieved literature. Please try rephrasing your question or ask about a "
    "related veterinary topic."
)


async def _chat_stream(
    query: str,
    chroma_collection: chromadb.Collection | None = None,
    user_id: str | None = None,
    history: list | None = None,
    prior_citations: list | None = None,
) -> AsyncGenerator[str, None]:
    settings = get_settings()

    # ── Step 1: Emergency detection ───────────────────────────────────────────
    detector = get_detector()
    emergency = detector.check(query)
    emergency_resources = emergency.resources if emergency.is_emergency else []

    # Retrieval intent — drives tox-journal boosting + wider pre-rerank window.
    # Based on emergency category (if any) plus tox-vocabulary + species check.
    intent = tox_intent.classify_intent(
        query, emergency.category if emergency.is_emergency else None
    )
    is_tox_query = intent == "toxicology"

    claude = ClaudeService(api_key=settings.anthropic_api_key, model=settings.claude_model)
    loop = asyncio.get_running_loop()

    # ── Step 1b: Emergency preliminary card (fires instantly, before any network call) ──
    if emergency.is_emergency and emergency.preliminary:
        yield _event({
            "type": "emergency_preliminary",
            "payload": {
                "category": emergency.category,
                "heading": emergency.preliminary["heading"],
                "priorities": emergency.preliminary["priorities"],
            },
        })

    # ── Follow-up fast path: reuse parent turn's evidence ─────────────────────
    # For same-case follow-ups ("what are the cure molecules?" after an FIP
    # answer), re-running retrieval is both slow and lower quality (terse
    # follow-up text is a bad search query). When the frontend supplies the
    # parent turn's citations we skip refinement + retrieval + rerank entirely
    # and hand Claude the prior evidence directly. Latency drops ~7s; the
    # reference panel stays visually stable across the conversation.
    # Prior-citations alone is sufficient signal — if the frontend populated
    # it, the user is intentionally continuing the same case. History was
    # previously required but that made the fast path fire inconsistently.
    reuse_prior = bool(prior_citations)

    if reuse_prior:
        yield _event({"type": "progress", "step": 1, "label": "Continuing with prior evidence…", "icon": "🧠"})
        yield _event({
            "type": "progress", "step": 2,
            "label": f"Reusing {len(prior_citations)} references from earlier in this case…",
            "icon": "📚",
        })
        yield _event({"type": "progress", "step": 3, "label": "Drafting case update…", "icon": "📄"})
        search_query = query
        api_errors: list[str] = []
        live_results = []
        chroma_chunks = []
        total_sources = len(prior_citations)
    else:
        # ── Step 2: Refine query for academic search ──────────────────────────
        yield _event({"type": "progress", "step": 1, "label": "Understanding your question…", "icon": "🧠"})
        search_query = await loop.run_in_executor(None, claude.refine_query, query)

    if not reuse_prior:
        # ── Step 3: Live API search + ChromaDB vector search (parallel) ───────
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

        # Run live API search, HyDE expansion, and ChromaDB vector search concurrently.
        # Tox queries get a wider pre-rerank window (40 vs 20) because tox
        # vocabulary is narrow and the corpus is sparse — give the reranker
        # more material to choose from.
        live_task = loop.run_in_executor(None, search_live, search_query, settings, 5)
        hyde_task = (
            loop.run_in_executor(None, hyde_expand, query, claude)
            if settings.use_hyde else None
        )
        n_pre_rerank = 40 if is_tox_query else 20
        boost_set = tox_intent.TOX_JOURNAL_NAMES if is_tox_query else None

        chroma_chunks: list[RetrievedChunk] = []
        if chroma_collection is not None:
            # Start with retrieval against the refined (keyword-compressed) query.
            chroma_raw = await loop.run_in_executor(
                None, chroma_search, search_query, chroma_collection,
                n_pre_rerank, settings.embedding_model,
            )
            seen_ids = {c.id for c in chroma_raw}

            # BUG-01 fix (WS7.1, 2026-04-21): refine_query compresses long
            # clinical vignettes to ≤8 words, which often loses the primary
            # entity — e.g. a pyometra-sepsis vignette gets refined to
            # "canine septic shock management" and pyometra-specific papers
            # miss top-k. For long queries (>80 chars) we also embed the raw
            # user query and union the results. Preserves the refined-query
            # ordering where both probes agree, adds rescued hits to the tail.
            if len(query) > 80 and query.strip() != search_query.strip():
                raw_raw = await loop.run_in_executor(
                    None, chroma_search, query, chroma_collection,
                    n_pre_rerank, settings.embedding_model,
                )
                for c in raw_raw:
                    if c.id not in seen_ids:
                        chroma_raw.append(c)
                        seen_ids.add(c.id)

            # HyDE: embed a hypothetical abstract alongside the raw query so
            # retrieval is done in abstract-space too. Unions with the prior
            # probes by chunk id, dedup-first-wins so the earlier ordering
            # is preserved where it agrees.
            if hyde_task is not None:
                try:
                    hyde_text = await hyde_task
                except Exception as exc:
                    _log.warning("HyDE expansion failed (non-fatal): %s", exc)
                    hyde_text = ""
                if hyde_text:
                    hyde_raw = await loop.run_in_executor(
                        None, chroma_search, hyde_text, chroma_collection,
                        n_pre_rerank, settings.embedding_model,
                    )
                    for c in hyde_raw:
                        if c.id not in seen_ids:
                            chroma_raw.append(c)
                            seen_ids.add(c.id)
            # Rerank against the ORIGINAL user query (not the keyword-only search_query)
            # so clinical intent ("stabilization", "first-line treatment") drives ranking.
            # For tox queries apply a small +0.3 rerank_score boost to chunks from
            # the curated tox-journal list (JVECC, Clinical Toxicology, etc.).
            chroma_chunks = rerank(
                query, chroma_raw, top_k=10,
                use_reranker=settings.use_reranker,
                boost_journals=boost_set,
            )

        search_result = await live_task
        live_results = search_result.resources
        api_errors   = search_result.errors

        # Apply the same cross-encoder relevance gate to live API results
        if live_results:
            live_results = await loop.run_in_executor(
                None, rerank_live, query, live_results, 8, settings.use_reranker
            )

        # ── Species filter: remove human-medicine papers; reorder by species match ─
        detected_species = detect_species(query)
        if live_results:
            live_results = filter_and_reorder(
                live_results, detected_species,
                get_text=lambda r: f"{r.title} {r.abstract}",
            )
        if chroma_chunks:
            chroma_chunks = filter_and_reorder(
                chroma_chunks, detected_species,
                get_text=lambda c: f"{c.title} {c.text}",
            )

        # ── Absolute-floor guard: if ALL reranked sources score below -3.0,
        # the reranker's min-4 floor has pulled tangential junk into the
        # panel. Treat this as "no retrieval" and route to the consensus
        # fallback — vets prefer an honest "literature synthesis incomplete"
        # banner over 4 sources of noise. (BUG-02 / WS7.4, 2026-04-21.)
        _ABSOLUTE_FLOOR = -3.0
        _all_scored = (
            [getattr(c, "rerank_score", 0.0) for c in chroma_chunks]
            + [getattr(r, "rerank_score", 0.0) for r in live_results]
        )
        all_below_floor = bool(_all_scored) and max(_all_scored) < _ABSOLUTE_FLOOR
        if all_below_floor:
            _log.info(
                "Absolute-floor guard: all %d reranked sources below %.1f; "
                "routing to consensus fallback.", len(_all_scored), _ABSOLUTE_FLOOR,
            )
            live_results = []
            chroma_chunks = []

        # ── No results from either source → graceful consensus fallback ───────
        # Previously we dumped an "API key error" message and the frontend
        # dropped the user back to the generic home state. Instead, generate
        # a short, safe consensus-based summary so the vet gets something
        # actionable at point of care. Explicit fallback_kind drives the
        # frontend recovery UI (Retry / Expand search buttons).
        if not live_results and not chroma_chunks:
            yield _event({
                "type": "progress", "step": 3,
                "label": "No direct literature match — producing consensus-based summary…",
                "icon": "🛟",
            })
            try:
                fallback_answer = await loop.run_in_executor(
                    None,
                    generate_consensus_fallback,
                    claude,
                    query,
                    emergency.category if emergency.is_emergency else None,
                )
            except Exception as exc:
                _log.warning("Consensus fallback generation failed: %s", exc)
                fallback_answer = (
                    "**Literature synthesis incomplete — consensus-based summary only.**\n\n"
                    "I was unable to retrieve peer-reviewed literature for this query and the "
                    "consensus fallback service is unavailable. Please retry in a moment, or "
                    "rephrase with more specific clinical context (species, signalment, presenting "
                    "signs) so retrieval can match.\n\n"
                    "If this is an active emergency, fall back to your clinic's standard "
                    "stabilisation protocol and escalate if the patient is deteriorating."
                )
            payload = {
                "answer": disclaimer_injector.inject(fallback_answer),
                "citations": [],
                "live_resources": [],
                "emergency": emergency.is_emergency,
                "resources": emergency_resources,
                "disclaimer": DISCLAIMER,
                "search_query": search_query,
                "retrieval_quality": "weak",
                "total_sources": 0,
                "cited_count": 0,
                "evidence_mode": "consensus",
                "fallback_kind": "no_retrieval",
                "evidence_counts": {"relevance": {}, "strength": {}},
                "hidden_references": [],
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
    if reuse_prior:
        context_block, citations = citation_builder.build_from_prior(prior_citations)
    elif live_results:
        live_block, live_citations = citation_builder.build_from_live(live_results)
        context_block, citations = citation_builder.merge(live_citations, live_block, chroma_chunks)
    else:
        context_block, citations = citation_builder.build(chroma_chunks)

    # ── Evidence floor: flag low-relevance contexts so Claude is honest about it ──
    _RELEVANT = lambda score: score >= 0.0  # moderate-or-better bucket
    strong_live    = sum(1 for r in live_results    if _RELEVANT(getattr(r, "rerank_score", 0)))
    strong_chroma  = sum(1 for c in chroma_chunks   if _RELEVANT(getattr(c, "rerank_score", 0)))
    strong_sources = strong_live + strong_chroma

    prefix_parts: list[str] = []
    if emergency.is_emergency:
        prefix_parts.append(f"[EMERGENCY: {emergency.category}] — use EMERGENCY MODE output format.")
    if strong_sources < 3:
        prefix_parts.append(
            f"⚠️ LOW-EVIDENCE CONDITIONS — only {strong_sources} directly relevant "
            f"source(s) were retrieved. You MUST: open with a brief "
            f"'Limited Direct Evidence' note; lean on [Clinical consensus] tier "
            f"where appropriate; keep the answer tight and do not pad with "
            f"tangential findings."
        )
    if prefix_parts:
        context_block = "\n".join(prefix_parts) + "\n\n" + context_block

    # ── Step 4: Stream Claude's answer as it generates ────────────────────────
    # Streaming delivers text chunks to the client within ~3-5 s of step 4
    # starting, replacing the previous "wait 40 s with zero feedback" UX
    # that made the product look frozen to QA testers.
    if reuse_prior:
        yield _event({"type": "progress", "step": 4, "label": "Writing case update…", "icon": "✍️"})
    else:
        yield _event({"type": "progress", "step": 4, "label": "Writing answer…", "icon": "✍️"})

    # Tighter max_tokens for follow-ups (delta format is short by design) —
    # cuts the upper bound on generation time.
    max_tokens = 1500 if (reuse_prior or history) else 3000

    # Bridge between the sync Claude stream (runs in a worker thread) and
    # the async SSE generator (this function). Items on the queue are one of:
    #   ("chunk", text)  — a delta to forward to the client
    #   ("done",  full)  — end of stream with accumulated text
    #   ("error", msg)   — generation failed
    #   ("ping",  "")    — keepalive ping tick (only when no chunks flowing)
    _chunk_queue: asyncio.Queue = asyncio.Queue()

    def _pump_stream() -> None:
        """Runs in a worker thread; iterates the sync Claude stream and
        pushes each chunk onto the asyncio queue using call_soon_threadsafe."""
        parts: list[str] = []
        try:
            for delta in claude.stream(query, context_block, max_tokens, history=history):
                parts.append(delta)
                loop.call_soon_threadsafe(_chunk_queue.put_nowait, ("chunk", delta))
            loop.call_soon_threadsafe(_chunk_queue.put_nowait, ("done", "".join(parts)))
        except Exception as exc:
            _log.exception("Claude stream failed: %s", exc)
            loop.call_soon_threadsafe(
                _chunk_queue.put_nowait,
                ("error", "".join(parts) or ""),
            )

    # Kick off the stream in a worker thread
    stream_task = loop.run_in_executor(None, _pump_stream)

    # Heartbeat: fire a ping if no chunk has arrived for >20 s (Railway TCP
    # idle-timeout protection). Cancelled as soon as the stream completes.
    last_activity = [asyncio.get_event_loop().time()]

    async def _stream_heartbeat() -> None:
        try:
            while True:
                await asyncio.sleep(15)
                if asyncio.get_event_loop().time() - last_activity[0] > 15:
                    await _chunk_queue.put(("ping", ""))
        except asyncio.CancelledError:
            pass

    ping_task = asyncio.create_task(_stream_heartbeat())

    # Graceful fallback — if the stream stalls for >90 s of inactivity OR
    # the overall generation exceeds 120 s, finalise with whatever we've
    # accumulated plus an explicit "partial answer" marker. Users always
    # get something back; they never stare at a frozen bubble.
    _STREAM_IDLE_TIMEOUT = 90   # seconds of silence before giving up
    _STREAM_HARD_CAP     = 120  # overall wall-clock safety net

    accumulated: list[str] = []
    answer_raw = ""
    start_ts = asyncio.get_event_loop().time()

    try:
        while True:
            now = asyncio.get_event_loop().time()
            if now - start_ts > _STREAM_HARD_CAP:
                answer_raw = "".join(accumulated) + (
                    "\n\n⚠️ *Partial answer — generation exceeded time limit. "
                    "Please retry for full version.*"
                )
                break
            try:
                kind, payload = await asyncio.wait_for(
                    _chunk_queue.get(), timeout=_STREAM_IDLE_TIMEOUT
                )
            except asyncio.TimeoutError:
                answer_raw = "".join(accumulated) + (
                    "\n\n⚠️ *Partial answer — generation stalled. "
                    "Please retry for full version.*"
                )
                break

            last_activity[0] = asyncio.get_event_loop().time()
            if kind == "chunk":
                accumulated.append(payload)
                yield _event({"type": "answer_chunk", "delta": payload})
            elif kind == "ping":
                yield _event({"type": "ping"})
            elif kind == "done":
                answer_raw = payload or "".join(accumulated)
                break
            elif kind == "error":
                answer_raw = "".join(accumulated) or (
                    "I wasn't able to generate an answer due to a temporary error. "
                    "Please try again in a moment."
                )
                break
    finally:
        ping_task.cancel()
        try:
            await stream_task
        except Exception:
            pass

    # ── Citation guard: block hallucinated structured answers with no citations ──
    # Fires only if Claude produced structured headings AND used ZERO trust tags.
    # Answers using only [Consensus]/[Guideline] (no [N]) are legitimate for
    # standard-of-care questions. When the guard fires we now generate a proper
    # consensus fallback instead of dumping a generic "try again" message, so
    # the vet still gets safe actionable guidance.
    citation_guard_fired = (
        not _TRUST_TAG_PATTERN.search(answer_raw)
        and _STRUCTURED_ANSWER_PATTERN.search(answer_raw)
    )
    timeout_partial_fired = "*Partial answer —" in answer_raw
    if citation_guard_fired:
        _log.warning("Citation guard triggered (structured, uncited) for query: %s", query[:120])
        try:
            answer_raw = await loop.run_in_executor(
                None,
                generate_consensus_fallback,
                claude,
                query,
                emergency.category if emergency.is_emergency else None,
            )
        except Exception:
            answer_raw = _NO_CITATION_ANSWER
        citations = []

    # ── Retrieval quality signal ──────────────────────────────────────────────
    cited_refs = set(re.findall(r"\[(\d+)\]", answer_raw))
    n_cited = len(cited_refs)
    if citation_guard_fired or n_cited <= 1:
        retrieval_quality = "weak"
    elif n_cited >= 5:
        retrieval_quality = "strong"
    else:
        retrieval_quality = "moderate"

    # ── Reference hygiene: separate cited / kept / hidden ─────────────────────
    # Three buckets now (was two):
    #   cited_refs          — Claude used [N] in the answer; always shown
    #   kept (high rel)     — uncited but high cross-encoder relevance; shown
    #   hidden (moderate-)  — uncited and only moderate/tangential; surfaced
    #                         in the frontend's "Retrieved but not used"
    #                         collapsible so the vet can see what was pulled
    # This restores trust for the "where did my sources go?" UX pain point.
    cited_str_set = cited_refs  # already a set of strings from the regex
    _total_before = len(citations)
    _kept: list = []
    _hidden: list = []
    # Keep uncited citations in the main panel only when their raw cross-encoder
    # score indicates they were strongly on-topic (≥1.0 ≈ "high" bucket).
    # Using rerank_score directly instead of the old `relevance` bucket field
    # because relevance now means something different (the new two-axis model).
    for c in citations:
        if str(c.ref) in cited_str_set or getattr(c, "rerank_score", 0.0) >= 1.0:
            _kept.append(c)
        else:
            _hidden.append(c)
    citations = _kept
    hidden_citations = _hidden
    live_results = [
        r for i, r in enumerate(live_results, start=1)
        if str(i) in cited_str_set or getattr(r, "rerank_score", 0.0) >= 3.0
    ]
    if _total_before != len(citations):
        _log.info(
            "Reference hygiene: hid %d/%d off-topic refs from panel",
            _total_before - len(citations), _total_before,
        )

    answer = disclaimer_injector.inject(answer_raw)

    # Populate intext_passage and relevant_quote for each citation
    for c in citations:
        c.intext_passage = _extract_intext_passage(answer, c.ref)
        c.relevant_quote = _extract_relevant_quote(answer, c.ref, c.abstract)

    # ── Enrich citations with clinician-readable metadata ─────────────────────
    # study_type, species_relevance, relevance axis, strength axis, heuristic
    # why_it_matters. The LLM rationale (below) overlays the heuristic text
    # for citations we can ground against their abstract.
    evidence_tagger.enrich(citations, query=query)
    evidence_tagger.enrich(hidden_citations, query=query)

    # ── Determine evidence_mode + fallback_kind for the response envelope ─────
    # evidence_mode tells the frontend what kind of answer this is so the UI
    # can show the right framing (literature-grounded vs consensus-only etc).
    if citation_guard_fired:
        evidence_mode = "consensus"
        fallback_kind: str | None = "guard_blocked"
    elif timeout_partial_fired:
        evidence_mode = "partial"
        fallback_kind = "timeout_partial"
    elif not citations:
        evidence_mode = "gap"
        fallback_kind = None
    elif n_cited == 0:
        evidence_mode = "consensus"
        fallback_kind = None
    else:
        evidence_mode = "literature"
        fallback_kind = None

    # LLM-generated "why it matters" overlay — two tiers.
    #   Tier B (batched, ≤22 words) runs first for ALL citations — cheap and
    #          keeps cards informative even when nothing else grounds.
    #   Tier A (per-direct, ~50 words, claim-linked) runs second for DIRECT
    #          citations only — overwrites Tier B so vets get the deeper
    #          rationale on the sources they'll actually act on.
    # Both tiers skipped in consensus-only modes (no sources to ground against).
    if evidence_mode == "literature" and citations:
        try:
            rationales_b = await loop.run_in_executor(
                None,
                why_it_matters_service.generate_rationales,
                query,
                citations,
                claude,
            )
            why_it_matters_service.overlay(citations, rationales_b)
        except Exception as exc:
            _log.warning("why_it_matters Tier B overlay failed (non-fatal): %s", exc)

        try:
            rationales_a = await loop.run_in_executor(
                None,
                why_it_matters_service.generate_deep_rationales,
                query,
                citations,
                claude,
                answer_raw,
            )
            why_it_matters_service.overlay(citations, rationales_a)
        except Exception as exc:
            _log.warning("why_it_matters Tier A overlay failed (non-fatal): %s", exc)

    evidence_counts = evidence_tagger.counts_by_axes(citations)

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
        "retrieval_quality": retrieval_quality,
        "total_sources": total_sources,
        "cited_count": n_cited,
        "evidence_mode": evidence_mode,
        "fallback_kind": fallback_kind,
        "evidence_counts": evidence_counts,
        "hidden_references": [c.model_dump() for c in hidden_citations],
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
        _chat_stream(
            body.query.strip(),
            chroma_collection=chroma_collection,
            user_id=user_id,
            history=body.history,
            prior_citations=body.prior_citations,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
