"""
Builds numbered citation blocks for Claude prompts and API response payloads.
Supports both Chroma chunks (offline/T&F) and live API results (online).
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
        source = "Taylor & Francis" if chunk.publisher == "Taylor & Francis" else chunk.source_type

        header = f"[{i}] {chunk.authors} ({chunk.year}). \"{chunk.title}\" — {chunk.journal} [{publisher}]."
        if chunk.doi:
            header += f" DOI: {chunk.doi}"
        elif chunk.url:
            header += f" URL: {chunk.url}"
        lines.append(header)
        lines.append(chunk.text)
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
            lines.append(r.abstract)
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
        source = "Taylor & Francis" if chunk.publisher == "Taylor & Francis" else chunk.source_type

        header = f"[{offset_idx}] {chunk.authors} ({chunk.year}). \"{chunk.title}\" — {chunk.journal} [{publisher}]."
        if chunk.doi:
            header += f" DOI: {chunk.doi}"
        elif chunk.url:
            header += f" URL: {chunk.url}"
        extra_lines.append(header)
        extra_lines.append(chunk.text)
        extra_lines.append("")

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
