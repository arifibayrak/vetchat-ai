"""
Cross-encoder reranker.
Model: cross-encoder/ms-marco-MiniLM-L-6-v2
Falls back to cosine distance order if USE_RERANKER=false or model unavailable.
"""
from __future__ import annotations

from app.services.retriever import RetrievedChunk

_cross_encoder = None
_load_attempted = False


def _get_cross_encoder():
    global _cross_encoder, _load_attempted
    if _load_attempted:
        return _cross_encoder
    _load_attempted = True
    try:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    except Exception:
        _cross_encoder = None
    return _cross_encoder


def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    top_k: int = 5,
    use_reranker: bool = True,
) -> list[RetrievedChunk]:
    """
    Rerank chunks using cross-encoder. Falls back to cosine order.
    Returns top_k results.
    """
    if not chunks:
        return []

    if use_reranker:
        model = _get_cross_encoder()
        if model is not None:
            pairs = [(query, chunk.text) for chunk in chunks]
            scores = model.predict(pairs)
            ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
            return [chunk for _, chunk in ranked[:top_k]]

    # Fallback: return top_k by ascending distance (cosine similarity)
    return sorted(chunks, key=lambda c: c.distance)[:top_k]
