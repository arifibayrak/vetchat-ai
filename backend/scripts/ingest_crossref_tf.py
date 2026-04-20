#!/usr/bin/env python
"""
Ingest real article abstracts from the 108 Taylor & Francis veterinary
journals via the Crossref public API.

Why this exists
---------------
The original `seed_taylor_francis.py` only seeded 108 journal-level metadata
stubs (title + ISSN + URL). That made retrieval return ~4 irrelevant results
on almost every clinical query — there were no articles in the store, only
journal directory entries.

This script pulls up to N recent, abstract-bearing articles per journal from
Crossref (no API key required, just a polite mailto), chunks them, embeds
them, and upserts into ChromaDB under `source_type: "article"` so they
participate in the normal retrieval + rerank pipeline.

Usage
-----
    cd backend
    python scripts/ingest_crossref_tf.py --per-journal 100

Resume-safe: skips DOIs already in the collection. Rate-limited to respect
Crossref's public API guidelines (~1 req/sec per journal).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from app.config import Settings
from app.ingestion.chunker import chunk_text
from app.ingestion.embedder import embed_texts

_JOURNALS_FILE = Path(__file__).parent.parent / "data" / "taylor_francis_journals.json"
_CROSSREF_WORKS = "https://api.crossref.org/works"
_UA = "Arlo-VetChat/0.1 (mailto:hello@askarlo.co.uk)"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_log = logging.getLogger("ingest_crossref")


def _strip_jats(text: str) -> str:
    """Crossref abstracts come wrapped in JATS XML (<jats:p>, <jats:italic>)."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _query_journal(client: httpx.Client, issn: str, rows: int) -> list[dict]:
    """Query Crossref for recent, abstract-bearing articles in a journal."""
    params = {
        "filter": f"issn:{issn},has-abstract:true,type:journal-article",
        "rows": str(rows),
        "sort": "published",
        "order": "desc",
        "select": "DOI,title,abstract,container-title,published-print,published-online,author,volume,issue,page,type,is-referenced-by-count,publisher",
    }
    try:
        r = client.get(_CROSSREF_WORKS, params=params, timeout=30)
        if r.status_code != 200:
            _log.warning("Crossref %s -> %d", issn, r.status_code)
            return []
        items = r.json().get("message", {}).get("items", [])
        return items
    except Exception as exc:
        _log.warning("Crossref query failed for ISSN %s: %s", issn, exc)
        return []


def _item_year(item: dict) -> int:
    for key in ("published-print", "published-online"):
        parts = item.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except Exception:
                pass
    return 0


def _item_authors(item: dict) -> str:
    authors = item.get("author") or []
    if not authors:
        return ""
    first = authors[0]
    family = first.get("family") or first.get("name") or ""
    if len(authors) == 1:
        return family
    return f"{family} et al."


def _chunk_id(doi: str, idx: int) -> str:
    h = hashlib.sha256(doi.encode()).hexdigest()[:12]
    return f"cr_{h}_{idx}"


def _existing_dois(collection: chromadb.Collection) -> set[str]:
    try:
        got = collection.get(include=["metadatas"])
        return {
            (m.get("doi") or "").lower()
            for m in (got.get("metadatas") or [])
            if m and m.get("doi")
        }
    except Exception:
        return set()


def ingest(
    collection: chromadb.Collection,
    per_journal: int,
    embedding_model: str,
    min_abstract_len: int = 200,
    sleep_between: float = 1.0,
) -> tuple[int, int, int]:
    """Returns (journals_scanned, articles_ingested, chunks_upserted)."""
    with open(_JOURNALS_FILE) as f:
        data = json.load(f)
    journals = data["journals"]

    existing = _existing_dois(collection)
    _log.info("ChromaDB currently holds %d DOIs — will skip duplicates.", len(existing))

    total_articles = 0
    total_chunks = 0
    scanned = 0

    with httpx.Client(headers={"User-Agent": _UA, "Accept": "application/json"}) as client:
        for j in journals:
            issn = j.get("online_issn") or j.get("print_issn")
            title = j.get("title", "unknown")
            if not issn:
                continue
            scanned += 1
            _log.info("[%d/%d] Querying %s (ISSN %s)…", scanned, len(journals), title, issn)

            items = _query_journal(client, issn, per_journal)
            if not items:
                time.sleep(sleep_between)
                continue

            batch_ids: list[str] = []
            batch_docs: list[str] = []
            batch_metas: list[dict] = []

            for item in items:
                doi = (item.get("DOI") or "").lower()
                if not doi or doi in existing:
                    continue
                abstract = _strip_jats(item.get("abstract") or "")
                if len(abstract) < min_abstract_len:
                    continue

                item_title = " ".join((item.get("title") or [])).strip()
                if not item_title:
                    continue

                container = " ".join((item.get("container-title") or [])).strip() or title
                year = _item_year(item)
                authors = _item_authors(item)
                volume = str(item.get("volume") or "")
                issue = str(item.get("issue") or "")
                pages = str(item.get("page") or "")
                cited_by = int(item.get("is-referenced-by-count") or 0)
                publisher = item.get("publisher") or "Taylor & Francis"

                # Embed one chunk per article — abstracts are short enough
                # that sub-chunking adds noise. If abstract is very long,
                # chunker will split it.
                full_text = f"{item_title}. {abstract}"
                chunks = chunk_text(full_text)
                for idx, chunk in enumerate(chunks):
                    batch_ids.append(_chunk_id(doi, idx))
                    batch_docs.append(chunk)
                    batch_metas.append({
                        "doi": doi,
                        "title": item_title,
                        "journal": container,
                        "year": year,
                        "authors": authors,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "source_type": "article",
                        "publisher": publisher,
                        "url": f"https://doi.org/{doi}",
                        "abstract": abstract,
                        "volume": volume,
                        "issue": issue,
                        "pages": pages,
                        "cited_by": cited_by,
                        "doc_type": (item.get("type") or "journal-article"),
                    })
                    total_chunks += 1
                existing.add(doi)
                total_articles += 1

            if batch_ids:
                try:
                    embeddings = embed_texts(batch_docs, model_name=embedding_model)
                    collection.upsert(
                        ids=batch_ids,
                        documents=batch_docs,
                        embeddings=embeddings,
                        metadatas=batch_metas,
                    )
                    _log.info("  → upserted %d chunks from %d new articles",
                              len(batch_ids), len(set(m["doi"] for m in batch_metas)))
                except Exception as exc:
                    _log.error("  !! upsert failed for %s: %s", title, exc)

            time.sleep(sleep_between)

    return scanned, total_articles, total_chunks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chroma-path", default=None,
                        help="ChromaDB path (defaults to settings.chroma_path)")
    parser.add_argument("--per-journal", type=int, default=100,
                        help="Max articles per journal (default 100 = ~10k target corpus)")
    parser.add_argument("--sleep", type=float, default=1.0,
                        help="Seconds between journal queries (Crossref politeness)")
    args = parser.parse_args()

    import os
    # Allow running without ANTHROPIC_API_KEY set
    os.environ.setdefault("ANTHROPIC_API_KEY", "offline-ingest")
    settings = Settings()
    chroma_path = args.chroma_path or settings.chroma_path

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )

    scanned, articles, chunks = ingest(
        collection,
        per_journal=args.per_journal,
        embedding_model=settings.embedding_model,
        sleep_between=args.sleep,
    )
    _log.info("Done. Scanned %d journals, ingested %d articles (%d chunks).",
              scanned, articles, chunks)


if __name__ == "__main__":
    main()
