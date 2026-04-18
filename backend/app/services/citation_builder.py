"""
Builds numbered citation blocks for Claude prompts and API response payloads.
Supports both Chroma chunks (offline/T&F) and live API results (online).

Context budget strategy (keeps Claude fast without losing cite-ability):
  - Top 3 sources (by reranker order) → up to 2500 chars (deep)
  - Remaining sources → up to 900 chars head+tail (summary)
  - Live abstracts are soft-capped at 1500 chars (most are already shorter)
Hard per-source cap prevents oversized chunks blowing context budget.
"""
from app.models.chat import CitationItem
from app.services.retriever import RetrievedChunk

# Map API source names to their parent publishers
_PUBLISHER_MAP: dict[str, str] = {
    "Scopus": "Elsevier",
    "ScienceDirect": "Elsevier",
    "Springer Nature": "Springer Nature",
    "Taylor & Francis": "Taylor & Francis",
}

# Context-budget knobs
_PRIMARY_BUDGET = 2500   # chars per top-ranked chunk
_SECONDARY_BUDGET = 900  # chars per lower-ranked chunk
_PRIMARY_COUNT = 3       # how many chunks get the primary budget
_LIVE_BUDGET = 1500      # soft cap for live abstracts


def _budget_text(text: str, budget: int) -> str:
    """Head + tail truncation; preserves opening context and conclusion."""
    if not text or len(text) <= budget:
        return text
    head_size = int(budget * 0.6)
    tail_size = max(budget - head_size - 40, 0)  # 40 chars for elision marker
    head = text[:head_size].rstrip()
    tail = text[-tail_size:].lstrip() if tail_size else ""
    return f"{head}\n\n…[mid-section summarised for speed]…\n\n{tail}" if tail else head


def _budget_for_rank(rank: int) -> int:
    """Top ranked chunks get more room; tail chunks get a summary."""
    return _PRIMARY_BUDGET if rank < _PRIMARY_COUNT else _SECONDARY_BUDGET


def build(chunks: list[RetrievedChunk]) -> tuple[str, list[CitationItem]]:
    """
    Build context from pre-ingested Chroma chunks (T&F journal directory + mock).
    Returns (context_block, citations).
    """
    if not chunks:
        return "No relevant literature found.", []

    lines: list[str] = []
    citations: list[CitationItem] = []

    for i, chunk in enumerate(chunks, start=1):
        # Prefer direct URL (e.g. tandfonline.com) over DOI for T&F journal entries
        doi_url = chunk.url or (f"https://doi.org/{chunk.doi}" if chunk.doi else "")
        publisher = chunk.publisher or "Literature"
        raw_source = chunk.source_type if chunk.source_type not in ("abstract", "") else "Literature"
        source = chunk.publisher if chunk.publisher else raw_source

        header = f"[{i}] {chunk.authors} ({chunk.year}). \"{chunk.title}\" — {chunk.journal} [{publisher}]."
        if chunk.doi:
            header += f" DOI: {chunk.doi}"
        elif chunk.url:
            header += f" URL: {chunk.url}"
        lines.append(header)
        lines.append(_budget_text(chunk.text, _budget_for_rank(i - 1)))
        lines.append("")

        citations.append(CitationItem(
            ref=i,
            title=chunk.title,
            journal=chunk.journal,
            year=chunk.year,
            doi=chunk.doi,
            url=doi_url,
            authors=chunk.authors,
            publisher=publisher,
            source=source,
        ))

    return "\n".join(lines), citations


def build_from_live(live_results: list) -> tuple[str, list[CitationItem]]:
    """
    Build context from live API results (Scopus / Springer Nature).
    live_results: list[LiveResource] from live_search.search_live()
    Returns (context_block, citations).
    """
    if not live_results:
        return "No relevant literature found.", []

    lines: list[str] = []
    citations: list[CitationItem] = []

    for i, r in enumerate(live_results, start=1):
        doi_url = f"https://doi.org/{r.doi}" if r.doi else ""
        publisher = _PUBLISHER_MAP.get(r.source, r.source)
        header = f"[{i}] {r.authors} ({r.year}). \"{r.title}\" — {r.journal} [{publisher}]."
        if r.doi:
            header += f" DOI: {r.doi}"
        lines.append(header)

        if r.abstract:
            lines.append(_budget_text(r.abstract, _LIVE_BUDGET))
        lines.append("")

        citations.append(CitationItem(
            ref=i,
            title=r.title,
            journal=r.journal,
            year=r.year,
            doi=r.doi,
            url=doi_url,
            authors=r.authors,
            abstract=r.abstract,
            volume=r.volume,
            issue=r.issue,
            pages=r.pages,
            doc_type=r.doc_type,
            cited_by=r.cited_by,
            publisher=publisher,
            source=r.source,
        ))

    return "\n".join(lines), citations


def merge(
    live_citations: list[CitationItem],
    live_block: str,
    chroma_chunks: list[RetrievedChunk],
) -> tuple[str, list[CitationItem]]:
    """
    Merge live API citations with ChromaDB chunks (T&F + mock) into one
    context block and numbered citation list. Live results come first.
    Deduplicates by DOI (or title if DOI absent).
    """
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    merged_citations: list[CitationItem] = []
    merged_lines: list[str] = []

    # — Live results first (already numbered 1..N in live_block)
    for c in live_citations:
        key = c.doi or c.title.lower()
        if c.doi:
            seen_dois.add(c.doi)
        else:
            seen_titles.add(c.title.lower())
        merged_citations.append(c)

    # Re-split live_block into per-citation segments (separated by blank lines)
    merged_lines.append(live_block.rstrip())

    # — ChromaDB chunks (T&F journals, mock data) appended after
    offset = len(merged_citations)
    extra_lines: list[str] = []
    chroma_rank = 0  # rank among chroma chunks that actually got added (for budgeting)

    for chunk in chroma_chunks:
        # Deduplicate
        if chunk.doi and chunk.doi in seen_dois:
            continue
        if not chunk.doi and chunk.title.lower() in seen_titles:
            continue

        if chunk.doi:
            seen_dois.add(chunk.doi)
        else:
            seen_titles.add(chunk.title.lower())

        ref_num = offset + len(extra_lines) // 3 + 1  # rough but safe
        offset_idx = len(merged_citations) + 1
        doi_url = chunk.url or (f"https://doi.org/{chunk.doi}" if chunk.doi else "")
        publisher = chunk.publisher or "Literature"
        raw_source = chunk.source_type if chunk.source_type not in ("abstract", "") else "Literature"
        source = chunk.publisher if chunk.publisher else raw_source

        header = f"[{offset_idx}] {chunk.authors} ({chunk.year}). \"{chunk.title}\" — {chunk.journal} [{publisher}]."
        if chunk.doi:
            header += f" DOI: {chunk.doi}"
        elif chunk.url:
            header += f" URL: {chunk.url}"
        extra_lines.append(header)
        extra_lines.append(_budget_text(chunk.text, _budget_for_rank(chroma_rank)))
        extra_lines.append("")
        chroma_rank += 1

        merged_citations.append(CitationItem(
            ref=offset_idx,
            title=chunk.title,
            journal=chunk.journal,
            year=chunk.year,
            doi=chunk.doi,
            url=doi_url,
            authors=chunk.authors,
            publisher=publisher,
            source=source,
        ))

    if extra_lines:
        merged_lines.append("\n".join(extra_lines))

    # Re-number all citations sequentially (live results keep their numbers; only appended chunks need new refs)
    final_block = "\n".join(merged_lines)
    return final_block, merged_citations
