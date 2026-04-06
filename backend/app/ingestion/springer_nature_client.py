"""
Springer Nature Meta API client.
Docs: https://dev.springernature.com/

Requires SPRINGER_NATURE_API_KEY in env.
Responses cached locally to avoid re-fetching.
"""
import hashlib
import json
import time
from pathlib import Path

import httpx

from app.ingestion.sciencedirect_client import ArticleMetadata, ConfigurationError

_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "cache"
_SEARCH_URL = "https://api.springernature.com/meta/v2/json"
_MIN_REQUEST_INTERVAL = 1 / 5  # 5 req/s (Springer free tier)


class SpringerNatureClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ConfigurationError(
                "SPRINGER_NATURE_API_KEY is not set. "
                "Add it to .env or leave blank to skip Springer ingestion."
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
        return _CACHE_DIR / f"springer_{h}.json"

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
        """
        Search Springer Nature Meta API.
        Returns a list of ArticleMetadata (abstract-level, no full-text).
        """
        params = {
            "q": query,
            "api_key": self._api_key,
            "p": count,          # results per page
            "s": 1,              # start index
        }
        data = self._cached_get(_SEARCH_URL, params)

        records = data.get("records", [])
        articles = []
        for rec in records:
            # Extract DOI
            doi = rec.get("doi", "")
            if not doi:
                # Try identifier list
                for ident in rec.get("identifier", []):
                    if ident.get("type") == "doi":
                        doi = ident.get("value", "")
                        break
            if not doi:
                continue

            # Extract year from publication date
            pub_date = rec.get("publicationDate", rec.get("coverDate", "2000-01-01"))
            year_str = pub_date[:4] if pub_date else "2000"
            year = int(year_str) if year_str.isdigit() else 2000

            # Authors
            creators = rec.get("creators", [])
            authors = ", ".join(
                c.get("creator", "") for c in creators[:3] if c.get("creator")
            )

            # Abstract
            abstract = rec.get("abstract", "")

            # Journal / publication name
            journal = rec.get("publicationName", rec.get("bookSeriesTitle", "Springer Nature"))

            articles.append(ArticleMetadata(
                doi=doi,
                title=rec.get("title", "Unknown title"),
                journal=journal,
                year=year,
                authors=authors,
                abstract=abstract,
                source_type="abstract",
            ))

        return articles
