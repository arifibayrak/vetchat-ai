"""
Live API search service.
Queries ScienceDirect and/or Springer Nature in real-time per user question.
Returns a list of LiveResource objects for display — does NOT ingest into Chroma.
"""
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass

from app.config import Settings


def _sanitise_error(source_name: str, exc: Exception) -> str:
    """
    Return a safe, human-readable error string.
    Never includes URLs or query parameters (which may contain API keys).
    """
    try:
        # httpx.HTTPStatusError has a .response attribute with .status_code
        status = exc.response.status_code  # type: ignore[union-attr]
        reasons = {
            401: "401 Unauthorized — check your API key",
            403: "403 Forbidden — your key may lack the required permissions",
            429: "429 Too Many Requests — rate limit exceeded",
            500: "500 Server Error",
        }
        msg = reasons.get(status, f"HTTP {status}")
    except AttributeError:
        # Network errors, timeouts, etc. — safe to show the type only
        msg = type(exc).__name__
    return f"{source_name}: {msg}"


@dataclass
class LiveResource:
    source: str          # "ScienceDirect" | "Springer Nature"
    title: str
    journal: str
    year: int
    authors: str
    doi: str
    url: str
    abstract: str


@dataclass
class SearchResult:
    resources: list[LiveResource]
    errors: list[str]   # e.g. ["ScienceDirect: 401 Unauthorized"]


def search_live(query: str, settings: Settings, max_results: int = 3) -> SearchResult:
    """
    Query all configured live sources concurrently.
    Returns SearchResult with resources and any errors encountered.
    """
    tasks: list[tuple[str, callable]] = []

    if settings.sciencedirect_api_key:
        tasks.append(("ScienceDirect", lambda: _search_sciencedirect(query, settings.sciencedirect_api_key, max_results)))

    if settings.springer_nature_api_key:
        tasks.append(("Springer Nature", lambda: _search_springer(query, settings.springer_nature_api_key, max_results)))

    if not tasks:
        return SearchResult(resources=[], errors=["No API keys configured"])

    resources: list[LiveResource] = []
    errors: list[str] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = {executor.submit(fn): name for name, fn in tasks}
        for future in concurrent.futures.as_completed(futures):
            source_name = futures[future]
            try:
                resources.extend(future.result())
            except Exception as e:
                # Sanitise: never expose URLs (which embed API keys) in error strings
                errors.append(_sanitise_error(source_name, e))

    return SearchResult(resources=resources, errors=errors)


def _search_sciencedirect(query: str, api_key: str, count: int) -> list[LiveResource]:
    """
    Search Elsevier Scopus (free developer tier).
    The legacy ScienceDirect Search endpoint requires institutional access;
    Scopus returns the same bibliographic metadata and includes citedby-count,
    which lets us surface the most-cited papers first.
    Fetches count*2 candidates and returns the top `count` by citation count.
    """
    import httpx

    params = {
        "query": query,
        "apiKey": api_key,
        "count": count,
        "view": "STANDARD",
        "sort": "relevancy",   # Scopus relevance ranking — best match first
        "httpAccept": "application/json",
    }
    with httpx.Client(timeout=15) as client:
        resp = client.get("https://api.elsevier.com/content/search/scopus", params=params)
        resp.raise_for_status()
        data = resp.json()

    resources = []
    for entry in data.get("search-results", {}).get("entry", []):
        doi = entry.get("prism:doi", "")
        if not doi:
            continue
        year_str = entry.get("prism:coverDate", "2000")[:4]
        # STANDARD view provides dc:creator (first author); full list needs COMPLETE
        first_author = entry.get("dc:creator", "")

        resources.append(LiveResource(
            source="Scopus",
            title=entry.get("dc:title", "Unknown title"),
            journal=entry.get("prism:publicationName", ""),
            year=int(year_str) if year_str.isdigit() else 2000,
            authors=first_author,
            doi=doi,
            url=f"https://doi.org/{doi}",
            abstract="",   # not available on free STANDARD view
        ))

    return resources


def _search_springer(query: str, api_key: str, count: int) -> list[LiveResource]:
    import httpx

    params = {
        "q": query,
        "api_key": api_key,
        "p": count,
        "s": 1,
    }
    with httpx.Client(timeout=10) as client:
        resp = client.get("https://api.springernature.com/meta/v2/json", params=params)
        resp.raise_for_status()
        data = resp.json()

    resources = []
    for rec in data.get("records", []):
        doi = rec.get("doi", "")
        if not doi:
            for ident in rec.get("identifier", []):
                if ident.get("type") == "doi":
                    doi = ident.get("value", "")
                    break
        if not doi:
            continue

        pub_date = rec.get("publicationDate", "2000-01-01")
        year_str = pub_date[:4]
        creators = rec.get("creators", [])
        authors = ", ".join(c.get("creator", "") for c in creators[:3] if c.get("creator"))

        resources.append(LiveResource(
            source="Springer Nature",
            title=rec.get("title", "Unknown title"),
            journal=rec.get("publicationName", rec.get("bookSeriesTitle", "Springer Nature")),
            year=int(year_str) if year_str.isdigit() else 2000,
            authors=authors,
            doi=doi,
            url=f"https://doi.org/{doi}",
            abstract=rec.get("abstract", ""),
        ))

    return resources
