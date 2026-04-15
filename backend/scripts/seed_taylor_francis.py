#!/usr/bin/env python
"""
Seed Taylor & Francis veterinary journals into ChromaDB.

Each journal is embedded as a searchable reference entry so Lenny can
surface the correct journal/URL when vets ask about specific topics or publications.

Usage:
    cd backend
    python scripts/seed_taylor_francis.py [--chroma-path ./chroma_store]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from app.config import Settings
from app.ingestion.embedder import embed_texts

_JOURNALS_FILE = Path(__file__).parent.parent / "data" / "taylor_francis_journals.json"


def _journal_id(title: str) -> str:
    return "tf_" + hashlib.sha256(title.encode()).hexdigest()[:12]


def _journal_to_text(j: dict) -> str:
    """Build a natural-language description of a journal for embedding."""
    parts = [f"Journal: {j['title']}"]
    if j["subtitle"]:
        parts.append(f"Subtitle: {j['subtitle']}")
    parts.append(f"Publisher: Taylor & Francis (tandfonline.com)")
    if j["print_issn"]:
        parts.append(f"Print ISSN: {j['print_issn']}")
    if j["online_issn"]:
        parts.append(f"Online ISSN: {j['online_issn']}")
    if j["url"]:
        parts.append(f"URL: {j['url']}")
    parts.append("Category: Veterinary Science and Animal Health")
    return " | ".join(parts)


def seed_taylor_francis(collection: chromadb.Collection, model: str = "all-MiniLM-L6-v2") -> int:
    with open(_JOURNALS_FILE) as f:
        data = json.load(f)

    journals = data["journals"]
    texts = [_journal_to_text(j) for j in journals]
    embeddings = embed_texts(texts, model_name=model)

    ids, docs, embs, metas = [], [], [], []
    for j, text, emb in zip(journals, texts, embeddings):
        ids.append(_journal_id(j["title"]))
        docs.append(text)
        embs.append(emb)
        metas.append({
            "doi": "",
            "title": j["title"],
            "journal": j["title"],
            "year": 2024,
            "authors": "Taylor & Francis",
            "chunk_index": 0,
            "total_chunks": 1,
            "source_type": "journal_directory",
            "publisher": "Taylor & Francis",
            "print_issn": j["print_issn"],
            "online_issn": j["online_issn"],
            "url": j["url"],
        })

    collection.upsert(ids=ids, documents=docs, embeddings=embs, metadatas=metas)
    return len(ids)


def main(chroma_path: str) -> None:
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )
    settings = Settings(anthropic_api_key="offline-seed", chroma_path=chroma_path)
    n = seed_taylor_francis(collection, model=settings.embedding_model)
    print(f"Seeded {n} Taylor & Francis journals into '{chroma_path}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chroma-path", default="./chroma_store")
    args = parser.parse_args()
    main(args.chroma_path)
