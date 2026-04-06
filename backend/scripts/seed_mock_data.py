#!/usr/bin/env python
"""
Offline seed script: loads mock JSONL data into ChromaDB.
No API key required.

Usage:
    python scripts/seed_mock_data.py [--chroma-path ./chroma_store]
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Make backend/app importable when run from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from app.config import Settings
from app.ingestion.pipeline import seed_mock


async def main(chroma_path: str) -> None:
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )
    settings = Settings(anthropic_api_key="offline-seed", chroma_path=chroma_path)
    n = await seed_mock(collection, settings)
    print(f"Seeded {n} chunks into '{chroma_path}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chroma-path", default="./chroma_store")
    args = parser.parse_args()
    asyncio.run(main(args.chroma_path))
