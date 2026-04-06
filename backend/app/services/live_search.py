"""
Live API search service.
Queries ScienceDirect (Scopus) and/or Springer Nature in real-time per user question.
Returns a list of LiveResource objects for display — does NOT ingest into Chroma.
"""
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field

from app.config import Settings


def _sanitise_error(source_name: str, exc: Exception) -> str:
    try:
        status = exc.response.status_code  # type: ignore[union-attr]
        reasons = {
            401: "401 Unauthorized — check your API key",
            403: "403 Forbidden — your key may lack the required permissions",
            429: "429 Too Many Requests — rate limit exceeded",
            500: "500 Server Error",
        }
        msg = reasons.get(status, f"HTTP {status}")
    except AttributeError:
        msg = type(exc).__name__
    return f"{source_name}: {msg}"


@dataclass
class LiveResource:
    source: str          # "Scopus" | "Springer Nature"
    title: str
    journal: str
    year: int
    authors: str
    doi: str
    url: str
    abstract: str
    # Citation metadata
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doc_type: str = ""   # "Article", "Review", "Conference Paper", etc.
    cited_by: int = 0


@dataclass
class SearchResult:
    resources: list[LiveResource]
    errors: list[str]


def search_live(query: str, settings: Settings, max_results: int = 3) -> SearchResult:
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
                errors.append(_sanitise_error(source_name, e))

    return SearchResult(resources=resources, errors=errors)


def _fetch_scopus_abstract(doi: str, api_key: str) -> str:
    """
    Fetch full abstract via Scopus Abstract Retrieval API (available on free tier).
    Returns empty string on any failure.
    """
    import httpx
    try:
        with httpx.Client(timeout=8) as client:
            resp = client.get(
                f"https://api.elsevier.com/content/abstract/doi/{doi}",
                params={"apiKey": api_key, "httpAccept": "application/json"},
            )
            if not resp.is_success:
                return ""
            data = resp.json()
        core = data.get("abstracts-retrieval-response", {}).get("coredata", {})
        return core.get("dc:description", "")
    except Exception:
        return ""


def _search_sciencedirect(query: str, api_key: str, count: int) -> list[LiveResource]:
    """
    Search via Scopus API (free developer tier).
    Extracts full citation metadata from STANDARD view, then fetches abstracts
    concurrently via the Abstract Retrieval API.
    """
    import httpx

    params = {
        "query": query,
        "apiKey": api_key,
        "count": count,
        "view": "STANDARD",
        "sort": "relevancy",
        "httpAccept": "application/json",
    }
    with httpx.Client(timeout=15) as client:
        resp = client.get("https://api.elsevier.com/content/search/scopus", params=params)
        resp.raise_for_status()
        data = resp.json()

    resources: list[LiveResource] = []
    for entry in data.get("search-results", {}).get("entry", []):
        doi = entry.get("prism:doi", "")
        if not doi:
            continue

        year_str = entry.get("prism:coverDate", "2000")[:4]
        first_author = entry.get("dc:creator", "")

        # Page range — prefer combined range, fall back to start page
        pages = (
            entry.get("prism:pageRange", "")
            or entry.get("prism:startingPage", "")
        )
        if pages and entry.get("prism:endingPage"):
            start = entry.get("prism:startingPage", "")
            end = entry.get("prism:endingPage", "")
            if start and end and "-" not in pages:
                pages = f"{start}–{end}"

        # Citation count
        cited_by_raw = entry.get("citedby-count", "0")
        try:
            cited_by = int(cited_by_raw)
        except (ValueError, TypeError):
            cited_by = 0

        # Direct Scopus page URL (better than bare DOI for the user)
        scopus_url = f"https://doi.org/{doi}"
        for link in entry.get("link", []):
            if link.get("@ref") == "scopus":
                scopus_url = link.get("@href", scopus_url)
                break

        resources.append(LiveResource(
            source="Scopus",
            title=entry.get("dc:title", "Unknown title"),
            journal=entry.get("prism:publicationName", ""),
            year=int(year_str) if year_str.isdigit() else 2000,
            authors=first_author,
            doi=doi,
            url=scopus_url,
            abstract="",  # filled below
            volume=entry.get("prism:volume", ""),
            issue=entry.get("prism:issueIdentifier", ""),
            pages=pages,
            doc_type=entry.get("subtypeDescription", ""),
            cited_by=cited_by,
        ))

    # Fetch abstracts concurrently (one request per paper)
    if resources:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(resources)) as pool:
            futures = {pool.submit(_fetch_scopus_abstract, r.doi, api_key): i for i, r in enumerate(resources)}
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                try:
                    resources[idx].abstract = future.result()
                except Exception:
                    pass

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

        # Page range from Springer
        start_page = rec.get("startingPage", "")
        end_page = rec.get("endingPage", "")
        if start_page and end_page:
            pages = f"{start_page}–{end_page}"
        elif start_page:
            pages = start_page
        else:
            pages = ""

        resources.append(LiveResource(
            source="Springer Nature",
            title=rec.get("title", "Unknown title"),
            journal=rec.get("publicationName", rec.get("bookSeriesTitle", "Springer Nature")),
            year=int(year_str) if year_str.isdigit() else 2000,
            authors=authors,
            doi=doi,
            url=f"https://doi.org/{doi}",
            abstract=rec.get("abstract", ""),
            volume=rec.get("volume", ""),
            issue=rec.get("number", ""),
            pages=pages,
            doc_type=rec.get("contentType", ""),
            cited_by=0,
        ))

    return resources
