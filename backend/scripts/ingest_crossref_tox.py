#!/usr/bin/env python
"""
Ingest toxicology / emergency veterinary abstracts from Crossref.

Why this exists
---------------
The T&F corpus (ingest_crossref_tf.py) is weighted toward Veterinary Nursing
Journal + Italian J Animal Science and has almost zero toxicology content.
Lily, xylitol, chocolate, allium, acetaminophen, rodenticide queries need
dedicated toxicology coverage — which lives on non-T&F publishers.

This script targets a curated list of toxicology + emergency journals on
Wiley, Elsevier, Oxford, Springer, etc., and FILTERS the returned articles
to vet-relevant toxicology only (keyword whitelist against title+abstract).
Non-vet toxicology papers are skipped so the corpus stays clean.

Resume-safe: dedups against DOIs already in Chroma.

Usage
-----
    cd backend
    python scripts/ingest_crossref_tox.py --per-journal 200
"""
from __future__ import annotations

import argparse
import hashlib
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

_CROSSREF_WORKS = "https://api.crossref.org/works"
_UA = "Arlo-VetChat/0.1 (mailto:hello@askarlo.co.uk)"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_log = logging.getLogger("ingest_tox")

# Curated toxicology / emergency journals with verified ISSNs (Crossref checked).
# title is just for logging. issn must be a valid registered ISSN.
_JOURNALS: list[dict] = [
    # Dedicated veterinary toxicology
    {"title": "Journal of Veterinary Emergency and Critical Care", "issn": "1476-4431"},
    {"title": "Veterinary and Comparative Oncology", "issn": "1476-5829"},
    # Medical / clinical toxicology — vet cases frequently published here
    {"title": "Journal of Medical Toxicology", "issn": "1937-6995"},
    {"title": "Clinical Toxicology", "issn": "1556-9519"},
    {"title": "Toxicology", "issn": "0300-483X"},
    {"title": "Toxicology Reports", "issn": "2214-7500"},
    {"title": "Toxicology and Applied Pharmacology", "issn": "0041-008X"},
    {"title": "Toxicologic Pathology", "issn": "1533-1601"},
    # General small-animal emergency + internal medicine (where tox commonly lands)
    {"title": "Journal of Small Animal Practice", "issn": "1748-5827"},
    {"title": "Journal of the American Veterinary Medical Association", "issn": "1943-569X"},
    {"title": "Journal of the American Animal Hospital Association", "issn": "1547-3317"},
    {"title": "Veterinary Record", "issn": "2042-7670"},
    {"title": "Journal of Veterinary Internal Medicine", "issn": "1939-1676"},
    {"title": "Veterinary Medicine and Science", "issn": "2053-1095"},
    {"title": "American Journal of Veterinary Research", "issn": "1943-5681"},
    {"title": "Frontiers in Veterinary Science", "issn": "2297-1769"},
    {"title": "BMC Veterinary Research", "issn": "1746-6148"},
    {"title": "Veterinary Clinical Pathology", "issn": "1939-165X"},
]

# Vet-toxicology keyword whitelist. An article must contain AT LEAST ONE
# of these strings in title or abstract to be ingested. Prevents non-vet
# pharmacology / industrial tox / human-only tox papers from polluting.
_TOX_KEYWORDS: list[str] = [
    # Iconic small-animal toxins
    "xylitol", "chocolate", "theobromine", "methylxanthine",
    "grape", "raisin", "allium", "onion", "garlic", "leek",
    "lily", "lilium",
    "acetaminophen", "paracetamol", "ibuprofen", "naproxen", "aspirin",
    "nsaid",
    "ethylene glycol", "antifreeze",
    "rodenticide", "anticoagulant rodenticide", "bromethalin", "brodifacoum",
    "permethrin", "pyrethroid",
    "metaldehyde", "slug bait",
    "strychnine", "organophosphate", "carbamate",
    "lead toxicity", "zinc toxicity",
    # Disease / presentation terms common in tox literature
    "toxicity", "toxicosis", "toxicology", "poisoning", "intoxication",
    "envenomation", "envenoming", "snake bite", "scorpion",
    "hepatotoxic", "nephrotoxic", "neurotoxic", "cardiotoxic",
    # Species qualifiers combined with tox terms (to keep vet-scoped)
    "dog", "canine", "cat", "feline", "puppy", "kitten",
    "equine", "bovine", "avian", "rabbit", "ferret",
    "veterinary", "small animal",
]


def _strip_jats(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_vet_tox_relevant(title: str, abstract: str) -> bool:
    """Keyword whitelist to keep the corpus vet-tox focused."""
    blob = f"{title} {abstract}".lower()
    # Must contain at least one tox term and one species qualifier
    # (species qualifier list is the last block of _TOX_KEYWORDS)
    tox_terms = set(_TOX_KEYWORDS[:40])
    species_terms = set(_TOX_KEYWORDS[40:])
    has_tox = any(t in blob for t in tox_terms)
    has_species = any(s in blob for s in species_terms)
    return has_tox and has_species


def _query_journal(client: httpx.Client, issn: str, rows: int) -> list[dict]:
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
        return r.json().get("message", {}).get("items", [])
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
    return f"tox_{h}_{idx}"


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


def ingest(collection, per_journal, embedding_model, min_abstract_len=200, sleep_between=1.0):
    existing = _existing_dois(collection)
    _log.info("ChromaDB currently holds %d DOIs — will skip duplicates.", len(existing))

    total_articles = 0
    total_chunks = 0
    total_skipped = 0

    with httpx.Client(headers={"User-Agent": _UA, "Accept": "application/json"}) as client:
        for i, j in enumerate(_JOURNALS, 1):
            issn = j["issn"]
            title = j["title"]
            _log.info("[%d/%d] Querying %s (ISSN %s)…", i, len(_JOURNALS), title, issn)

            items = _query_journal(client, issn, per_journal)
            if not items:
                time.sleep(sleep_between)
                continue

            batch_ids, batch_docs, batch_metas = [], [], []
            skipped_not_vet_tox = 0

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

                # Keyword whitelist — keep vet-tox only
                if not _is_vet_tox_relevant(item_title, abstract):
                    skipped_not_vet_tox += 1
                    continue

                container = " ".join((item.get("container-title") or [])).strip() or title
                year = _item_year(item)
                authors = _item_authors(item)
                publisher = item.get("publisher") or ""

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
                        "volume": str(item.get("volume") or ""),
                        "issue": str(item.get("issue") or ""),
                        "pages": str(item.get("page") or ""),
                        "cited_by": int(item.get("is-referenced-by-count") or 0),
                        "doc_type": (item.get("type") or "journal-article"),
                    })
                    total_chunks += 1
                existing.add(doi)
                total_articles += 1

            total_skipped += skipped_not_vet_tox
            if batch_ids:
                try:
                    embeddings = embed_texts(batch_docs, model_name=embedding_model)
                    collection.upsert(
                        ids=batch_ids, documents=batch_docs,
                        embeddings=embeddings, metadatas=batch_metas,
                    )
                    _log.info("  → upserted %d chunks from %d new articles (skipped %d non-vet-tox)",
                              len(batch_ids), len(set(m["doi"] for m in batch_metas)), skipped_not_vet_tox)
                except Exception as exc:
                    _log.error("  !! upsert failed for %s: %s", title, exc)
            elif skipped_not_vet_tox:
                _log.info("  → 0 new articles (skipped %d non-vet-tox)", skipped_not_vet_tox)

            time.sleep(sleep_between)

    return len(_JOURNALS), total_articles, total_chunks, total_skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chroma-path", default=None)
    parser.add_argument("--per-journal", type=int, default=200)
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    import os
    os.environ.setdefault("ANTHROPIC_API_KEY", "offline-ingest")
    settings = Settings()
    chroma_path = args.chroma_path or settings.chroma_path

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )

    scanned, articles, chunks, skipped = ingest(
        collection,
        per_journal=args.per_journal,
        embedding_model=settings.embedding_model,
        sleep_between=args.sleep,
    )
    _log.info("Done. Scanned %d journals, ingested %d vet-tox articles (%d chunks). Skipped %d non-vet-tox.",
              scanned, articles, chunks, skipped)


if __name__ == "__main__":
    main()
