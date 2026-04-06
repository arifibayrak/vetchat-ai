"""
Builds numbered citation blocks for Claude prompts and API response payloads.
Supports both Chroma chunks (offline) and live API results (online).
"""
from app.models.chat import CitationItem
from app.services.retriever import RetrievedChunk


def build(chunks: list[RetrievedChunk]) -> tuple[str, list[CitationItem]]:
    """
    Build context from pre-ingested Chroma chunks (offline / fallback path).
    Returns (context_block, citations).
    """
    if not chunks:
        return "No relevant literature found.", []

    lines: list[str] = []
    citations: list[CitationItem] = []

    for i, chunk in enumerate(chunks, start=1):
        doi_url = f"https://doi.org/{chunk.doi}" if chunk.doi else ""
        header = f"[{i}] {chunk.authors} ({chunk.year}). \"{chunk.title}\" — {chunk.journal}."
        if chunk.doi:
            header += f" DOI: {chunk.doi}"
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
        ))

    return "\n".join(lines), citations


def build_from_live(live_results: list) -> tuple[str, list[CitationItem]]:
    """
    Build context from live API results (ScienceDirect / Springer Nature).
    live_results: list[LiveResource] from live_search.search_live()
    Returns (context_block, citations).
    """
    if not live_results:
        return "No relevant literature found.", []

    lines: list[str] = []
    citations: list[CitationItem] = []

    for i, r in enumerate(live_results, start=1):
        doi_url = f"https://doi.org/{r.doi}" if r.doi else ""
        header = f"[{i}] {r.authors} ({r.year}). \"{r.title}\" — {r.journal} [{r.source}]."
        if r.doi:
            header += f" DOI: {r.doi}"
        lines.append(header)

        # Use abstract as context text
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
        ))

    return "\n".join(lines), citations
