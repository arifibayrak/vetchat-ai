#!/usr/bin/env python
"""
Inspect the state of the ChromaDB corpus.

Prints:
  - total document count
  - breakdown by source_type (article / journal_directory / other)
  - top 10 journals by chunk count
  - year histogram (articles only)
  - top 10 publishers by chunk count

Run against the same chroma_path the backend uses, e.g. after a Crossref
ingestion job on Railway to confirm articles actually landed.

Usage
-----
    cd backend
    python scripts/inspect_corpus.py [--chroma-path ./chroma_store]
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from app.config import Settings


def inspect(chroma_path: str) -> None:
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )

    total = collection.count()
    print(f"ChromaDB path      : {chroma_path}")
    print(f"Collection         : vet_literature")
    print(f"Total documents    : {total}")
    if total == 0:
        print("Collection is empty.")
        return

    got = collection.get(include=["metadatas"])
    metas = got.get("metadatas") or []

    source_types: Counter[str] = Counter()
    journals: Counter[str] = Counter()
    publishers: Counter[str] = Counter()
    years: Counter[int] = Counter()
    unique_dois: set[str] = set()

    for m in metas:
        if not m:
            continue
        source_types[m.get("source_type") or "unknown"] += 1
        journal = (m.get("journal") or "").strip() or "(no journal)"
        journals[journal] += 1
        publisher = (m.get("publisher") or "").strip() or "(no publisher)"
        publishers[publisher] += 1
        if (m.get("source_type") or "") == "article":
            y = m.get("year") or 0
            try:
                years[int(y)] += 1
            except (TypeError, ValueError):
                pass
        doi = (m.get("doi") or "").strip().lower()
        if doi:
            unique_dois.add(doi)

    print(f"Unique DOIs        : {len(unique_dois)}")
    print()
    print("── source_type breakdown ──")
    for st, n in source_types.most_common():
        print(f"  {st:<22} {n:>6}")
    print()
    print("── top 10 journals by chunk count ──")
    for j, n in journals.most_common(10):
        print(f"  {n:>5}  {j[:80]}")
    print()
    print("── top 10 publishers ──")
    for p, n in publishers.most_common(10):
        print(f"  {n:>5}  {p[:80]}")
    print()
    if years:
        print("── article year histogram ──")
        for y in sorted(years):
            bar = "#" * min(years[y], 60)
            print(f"  {y:>4}  {years[y]:>5}  {bar}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chroma-path", default=None)
    args = parser.parse_args()

    os.environ.setdefault("ANTHROPIC_API_KEY", "offline-inspect")
    settings = Settings()
    chroma_path = args.chroma_path or settings.chroma_path
    inspect(chroma_path)


if __name__ == "__main__":
    main()
