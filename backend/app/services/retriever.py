"""
Chroma retrieval service.
Embeds query, performs cosine similarity search, filters by distance threshold.
"""
from dataclasses import dataclass

import chromadb

from app.ingestion.embedder import embed_texts

DISTANCE_THRESHOLD = 0.8
DEFAULT_N_RESULTS = 10


@dataclass
class RetrievedChunk:
    id: str
    text: str
    distance: float
    doi: str
    title: str
    journal: str
    year: int
    authors: str
    chunk_index: int
    total_chunks: int
    source_type: str
    publisher: str = ""     # e.g. "Taylor & Francis" for T&F-seeded entries
    url: str = ""           # direct link (e.g. tandfonline.com for T&F journals)
    rerank_score: float = 0.0  # cross-encoder relevance score (set by reranker)


def search(
    query: str,
    collection: chromadb.Collection,
    n_results: int = DEFAULT_N_RESULTS,
    embedding_model: str = "all-MiniLM-L6-v2",
    distance_threshold: float = DISTANCE_THRESHOLD,
) -> list[RetrievedChunk]:
    """
    Embed query, search Chroma, filter by distance threshold.
    Returns empty list if collection is empty or no results pass threshold.
    """
    if collection.count() == 0:
        return []

    query_emb = embed_texts([query], model_name=embedding_model)[0]

    actual_n = min(n_results, collection.count())
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=actual_n,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievedChunk] = []
    for doc, meta, dist, cid in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        results["ids"][0],
    ):
        if dist >= distance_threshold:
            continue
        chunks.append(RetrievedChunk(
            id=cid,
            text=doc,
            distance=dist,
            doi=meta.get("doi", ""),
            title=meta.get("title", "Unknown"),
            journal=meta.get("journal", "Unknown"),
            year=int(meta.get("year", 2000)),
            authors=meta.get("authors", ""),
            chunk_index=int(meta.get("chunk_index", 0)),
            total_chunks=int(meta.get("total_chunks", 1)),
            source_type=meta.get("source_type", "Literature"),
            publisher=meta.get("publisher", ""),
            url=meta.get("url", ""),
        ))

    return chunks
