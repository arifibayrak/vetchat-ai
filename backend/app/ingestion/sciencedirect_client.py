"""
ScienceDirect / Elsevier API client.
Requires SCIENCEDIRECT_API_KEY in env.
Responses cached locally to avoid re-fetching.
"""
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
_SEARCH_URL = "https://api.elsevier.com/content/search/sciencedirect"
_ARTICLE_URL = "https://api.elsevier.com/content/article/doi/{doi}"
_MIN_REQUEST_INTERVAL = 1 / 6  # 6 req/s max


@dataclass
class ArticleMetadata:
    doi: str
    title: str
    journal: str
    year: int
    authors: str
    abstract: str
    fulltext: str | None = None
    source_type: str = "abstract"


class ConfigurationError(Exception):
    pass


class ScienceDirectClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ConfigurationError(
                "SCIENCEDIRECT_API_KEY is not set. "
                "Add it to .env or run seed_mock_data.py for offline testing."
            )
        self._api_key = api_key
        self._last_request_time = 0.0
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    def _cache_path(self, key: str) -> Path:
        h = hashlib.sha256(key.encode()).hexdigest()[:16]
        return _CACHE_DIR / f"{h}.json"

    def _cached_get(self, url: str, params: dict) -> dict:
        cache_key = url + json.dumps(params, sort_keys=True)
        path = self._cache_path(cache_key)
        if path.exists():
            with open(path) as f:
                return json.load(f)

        self._rate_limit()
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        with open(path, "w") as f:
            json.dump(data, f)
        return data

    def search(self, query: str, count: int = 25) -> list[ArticleMetadata]:
        params = {
            "query": query,
            "apiKey": self._api_key,
            "count": count,
            "field": "doi,title,publicationName,coverDate,authors,description",
            "httpAccept": "application/json",
        }
        data = self._cached_get(_SEARCH_URL, params)
        results = data.get("search-results", {}).get("entry", [])
        articles = []
        for entry in results:
            doi = entry.get("prism:doi", "")
            if not doi:
                continue
            year_str = entry.get("prism:coverDate", "2000")[:4]
            articles.append(ArticleMetadata(
                doi=doi,
                title=entry.get("dc:title", "Unknown title"),
                journal=entry.get("prism:publicationName", "Unknown journal"),
                year=int(year_str) if year_str.isdigit() else 2000,
                authors=entry.get("authors", {}).get("author", [{}])[0].get("$", "") if isinstance(entry.get("authors"), dict) else "",
                abstract=entry.get("dc:description", ""),
            ))
        return articles

    def fetch_fulltext(self, doi: str) -> str | None:
        """Return full text if available (open access), else None."""
        url = _ARTICLE_URL.format(doi=doi)
        params = {"apiKey": self._api_key, "httpAccept": "application/json"}
        try:
            data = self._cached_get(url, params)
            # Elsevier full-text response nests content under various keys
            body = (
                data.get("full-text-retrieval-response", {})
                    .get("originalText", None)
            )
            return body
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (403, 404, 429):
                return None
            raise

    def fetch_abstract(self, doi: str) -> str:
        """Return abstract text for the given DOI."""
        url = _ARTICLE_URL.format(doi=doi)
        params = {"apiKey": self._api_key, "httpAccept": "application/json", "view": "META_ABS"}
        try:
            data = self._cached_get(url, params)
            return (
                data.get("abstracts-retrieval-response", {})
                    .get("coredata", {})
                    .get("dc:description", "")
            )
        except httpx.HTTPStatusError:
            return ""
