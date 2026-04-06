#!/usr/bin/env python
"""
Online ingestion script: fetches from ScienceDirect and/or Springer Nature and upserts to ChromaDB.

Usage:
    # Ingest from all configured sources (auto-detects keys in .env)
    python scripts/ingest_sciencedirect.py \
        --queries "veterinary xylitol toxicology" "canine chocolate toxicity" \
        --count 25 \
        --chroma-path ./chroma_store

    # Ingest from Springer Nature only
    python scripts/ingest_sciencedirect.py \
        --queries "veterinary dermatology atopic" \
        --sources springer \
        --count 25

    # Ingest from ScienceDirect only
    python scripts/ingest_sciencedirect.py \
        --queries "feline respiratory" \
        --sources sciencedirect \
        --count 25
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from dotenv import load_dotenv
from app.config import Settings
from app.ingestion.pipeline import run_ingestion

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", nargs="+", required=True)
    parser.add_argument("--count", type=int, default=25)
    parser.add_argument("--chroma-path", default="./chroma_store")
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["sciencedirect", "springer"],
        default=None,
        help="Sources to ingest from. Defaults to all sources with configured API keys.",
    )
    args = parser.parse_args()

    settings = Settings(chroma_path=args.chroma_path)

    # Report which sources are active
    active = []
    if settings.sciencedirect_api_key:
        active.append("ScienceDirect")
    if settings.springer_nature_api_key:
        active.append("Springer Nature")
    if not active:
        print("ERROR: No API keys configured. Set SCIENCEDIRECT_API_KEY or SPRINGER_NATURE_API_KEY in .env")
        sys.exit(1)

    if args.sources:
        used = [s.capitalize() for s in args.sources]
    else:
        used = active

    print(f"Sources: {', '.join(used)}")
    print(f"Queries: {len(args.queries)}, Results per query: {args.count}")

    client = chromadb.PersistentClient(path=args.chroma_path)
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )

    result = run_ingestion(
        args.queries,
        collection,
        settings,
        count=args.count,
        sources=args.sources,
    )

    print(f"\nIngestion complete:")
    print(f"  Articles fetched:  {result['articles_fetched']}")
    print(f"  Chunks upserted:   {result['chunks_upserted']}")
    if result["errors"]:
        print(f"  Errors ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"    - {e}")


if __name__ == "__main__":
    main()
