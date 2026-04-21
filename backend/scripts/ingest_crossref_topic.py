#!/usr/bin/env python
"""
Ingest veterinary articles from Crossref scoped by TOPIC (not journal).

Why this exists
---------------
`ingest_crossref_tf.py` and `ingest_crossref_tox.py` both filter Crossref by
ISSN lists. That misses iconic vet topics that happen to live in journals
outside those curated lists — lily toxicosis papers from JAAHA, pyometra
case series from Reproduction in Domestic Animals, etc.

This script flips the filter: it queries Crossref's `query.bibliographic`
endpoint per topic (e.g. "lily toxicosis cats Lilium nephrotoxicity"),
pulls the top-N results with abstracts, keeps only those that also mention
a vet species keyword, and ingests them into ChromaDB. Resume-safe (DOI
dedup against what's already in the store).

Topic list lives in `backend/data/topic_queries.json`.

Usage
-----
    cd backend
    python scripts/ingest_crossref_topic.py
    python scripts/ingest_crossref_topic.py --only lily_toxicosis_cat
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
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

_TOPICS_FILE = Path(__file__).parent.parent / "data" / "topic_queries.json"
_CROSSREF_WORKS = "https://api.crossref.org/works"
_UA = "Arlo-VetChat/0.1 (mailto:hello@askarlo.co.uk)"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_log = logging.getLogger("ingest_topic")

# Species whitelist — an article must mention at least one of these in its
# title or abstract to be ingested. Keeps out human-pharma / zoology papers
# that hit the query by keyword but aren't vet-relevant.
_SPECIES_WHITELIST: frozenset[str] = frozenset({
    "dog", "dogs", "canine", "canines", "puppy", "puppies",
    "cat", "cats", "feline", "felines", "kitten", "kittens",
    "horse", "horses", "equine", "equines", "foal", "mare", "stallion",
    "cattle", "bovine", "calf", "calves", "cow", "cows", "bull", "heifer",
    "sheep", "ovine", "goat", "caprine",
    "pig", "pigs", "swine", "porcine", "piglet",
    "rabbit", "rabbits", "ferret", "ferrets",
    "bird", "birds", "avian", "poultry", "parrot", "psittacine",
    "veterinary", "vet",
})


def _strip_jats(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_vet_relevant(title: str, abstract: str) -> bool:
    blob = f"{title} {abstract}".lower()
    tokens = set(re.findall(r"[a-z]+", blob))
    return bool(tokens & _SPECIES_WHITELIST)


def _query_topic(client: httpx.Client, query_text: str, rows: int) -> list[dict]:
    params = {
        "query.bibliographic": query_text,
        "filter": "has-abstract:true,type:journal-article",
        "rows": str(rows),
        "sort": "relevance",
        "order": "desc",
        "select": "DOI,title,abstract,container-title,published-print,published-online,author,volume,issue,page,type,is-referenced-by-count,publisher",
    }
    try:
        r = client.get(_CROSSREF_WORKS, params=params, timeout=30)
        if r.status_code != 200:
            _log.warning("Crossref topic %r -> %d", query_text, r.status_code)
            return []
        return r.json().get("message", {}).get("items", [])
    except Exception as exc:
        _log.warning("Crossref topic query failed for %r: %s", query_text, exc)
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
    return f"topic_{h}_{idx}"


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
    topics: list[dict],
    embedding_model: str,
    min_abstract_len: int = 200,
    sleep_between: float = 1.0,
) -> tuple[int, int, int, int]:
    existing = _existing_dois(collection)
    _log.info("ChromaDB currently holds %d DOIs — will skip duplicates.", len(existing))

    total_articles = 0
    total_chunks = 0
    total_skipped = 0

    with httpx.Client(headers={"User-Agent": _UA, "Accept": "application/json"}) as client:
        for idx, t in enumerate(topics, 1):
            slug = t["slug"]
            query_text = t["query"]
            rows = int(t.get("per_topic", 30))
            _log.info("[%d/%d] %s — querying %r …", idx, len(topics), slug, query_text)

            items = _query_topic(client, query_text, rows)
            if not items:
                time.sleep(sleep_between)
                continue

            batch_ids: list[str] = []
            batch_docs: list[str] = []
            batch_metas: list[dict] = []
            skipped_non_vet = 0

            for item in items:
                doi = (item.get("DOI") or "").lower()
                if not doi or doi in existing:
                    continue
                abstract = _strip_jats(item.get("abstract") or "")
                if len(abstract) < min_abstract_len:
                    continue
                title = " ".join((item.get("title") or [])).strip()
                if not title:
                    continue

                if not _is_vet_relevant(title, abstract):
                    skipped_non_vet += 1
                    continue

                container = " ".join((item.get("container-title") or [])).strip()
                year = _item_year(item)
                authors = _item_authors(item)
                publisher = item.get("publisher") or ""

                full_text = f"{title}. {abstract}"
                chunks = chunk_text(full_text)
                for ci, chunk in enumerate(chunks):
                    batch_ids.append(_chunk_id(doi, ci))
                    batch_docs.append(chunk)
                    batch_metas.append({
                        "doi": doi,
                        "title": title,
                        "journal": container,
                        "year": year,
                        "authors": authors,
                        "chunk_index": ci,
                        "total_chunks": len(chunks),
                        "source_type": "article",
                        "publisher": publisher,
                        "url": f"https://doi.org/{doi}",
                        "abstract": abstract,
                        "volume": str(item.get("volume") or ""),
                        "issue": str(item.get("issue") or ""),
                        "pages": str(item.get("page") or ""),
                        "cited_by": int(item.get("is-referenced-by-count") or 0),
                        "doc_type": (item.get("type") or "journal-article"),
                        "topic_slug": slug,
                    })
                    total_chunks += 1
                existing.add(doi)
                total_articles += 1

            total_skipped += skipped_non_vet
            if batch_ids:
                try:
                    embeddings = embed_texts(batch_docs, model_name=embedding_model)
                    collection.upsert(
                        ids=batch_ids, documents=batch_docs,
                        embeddings=embeddings, metadatas=batch_metas,
                    )
                    _log.info(
                        "  → upserted %d chunks from %d new articles (skipped %d non-vet)",
                        len(batch_ids),
                        len({m["doi"] for m in batch_metas}),
                        skipped_non_vet,
                    )
                except Exception as exc:
                    _log.error("  !! upsert failed for %s: %s", slug, exc)
            elif skipped_non_vet:
                _log.info("  → 0 new articles (skipped %d non-vet)", skipped_non_vet)
            else:
                _log.info("  → 0 new articles (all duplicates or too short)")

            time.sleep(sleep_between)

    return len(topics), total_articles, total_chunks, total_skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chroma-path", default=None)
    parser.add_argument("--only", default=None, help="Restrict to one topic slug")
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    os.environ.setdefault("ANTHROPIC_API_KEY", "offline-ingest")
    settings = Settings()
    chroma_path = args.chroma_path or settings.chroma_path

    with open(_TOPICS_FILE) as f:
        topics = json.load(f)["topics"]
    if args.only:
        topics = [t for t in topics if t["slug"] == args.only]
        if not topics:
            _log.error("No topic found with slug=%s", args.only)
            sys.exit(1)

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )

    scanned, articles, chunks, skipped = ingest(
        collection,
        topics=topics,
        embedding_model=settings.embedding_model,
        sleep_between=args.sleep,
    )
    _log.info(
        "Done. Scanned %d topics, ingested %d articles (%d chunks). Skipped %d non-vet.",
        scanned, articles, chunks, skipped,
    )


if __name__ == "__main__":
    main()
