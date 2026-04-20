"""
Cross-encoder reranker.
Model: cross-encoder/ms-marco-MiniLM-L-6-v2
Falls back to cosine distance order if USE_RERANKER=false or model unavailable.

Applied to BOTH Chroma chunks AND live API abstracts so off-topic sources
can't slip through just by matching on species alone.
"""
from __future__ import annotations

from app.services.retriever import RetrievedChunk

_cross_encoder = None
_load_attempted = False

# ChromaDB: local data we trust; allow moderate threshold
# Tuned for MS-MARCO MiniLM against biomedical text — biomed abstracts
# typically score ~2 points lower than web-search training distribution.
_CHROMA_THRESHOLD = -2.0
# Live APIs: millions of papers, lots of tangential hits; stricter gate
_LIVE_THRESHOLD = -1.5
# Floor on how many results to return when threshold filter is too aggressive.
# Previously 2 — which forced almost every query to its floor and produced
# the chronic "only 4 sources" cap (2 live + 2 chroma).
_MIN_RESULTS = 4


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


def score_to_bucket(score: float) -> str:
    """Map a cross-encoder relevance score to a user-facing bucket."""
    if score >= 3.0:
        return "high"
    if score >= 0.0:
        return "moderate"
    return "tangential"


def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    top_k: int = 5,
    use_reranker: bool = True,
) -> list[RetrievedChunk]:
    """
    Rerank ChromaDB chunks. Attaches each chunk's cross-encoder score to
    `.rerank_score`. Filters below threshold with a min-2 fallback.
    """
    if not chunks:
        return []

    if use_reranker:
        model = _get_cross_encoder()
        if model is not None:
            pairs = [(query, chunk.text) for chunk in chunks]
            scores = model.predict(pairs)
            # Attach scores to every chunk for downstream citation tagging
            for chunk, score in zip(chunks, scores):
                chunk.rerank_score = float(score)
            ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
            above = [(s, c) for s, c in ranked if s >= _CHROMA_THRESHOLD]
            if len(above) < _MIN_RESULTS:
                above = ranked[:_MIN_RESULTS]
            return [c for _, c in above[:top_k]]

    return sorted(chunks, key=lambda c: c.distance)[:top_k]


def rerank_live(query: str, resources: list, top_k: int = 5, use_reranker: bool = True) -> list:
    """
    Score live API abstracts with cross-encoder and drop below threshold.
    Attaches score to each resource's `.rerank_score`. Prevents off-topic
    papers (e.g. feline bronchial disease returned for a urethral obstruction
    query) from ever reaching Claude or being displayed as sources.
    """
    if not resources:
        return []
    if not use_reranker:
        for r in resources:
            r.rerank_score = 0.0
        return resources[:top_k]

    model = _get_cross_encoder()
    if model is None:
        for r in resources:
            r.rerank_score = 0.0
        return resources[:top_k]

    pairs = [(query, f"{r.title}. {r.abstract}") for r in resources]
    scores = model.predict(pairs)
    for r, s in zip(resources, scores):
        r.rerank_score = float(s)

    ranked = sorted(zip(scores, resources), key=lambda x: x[0], reverse=True)
    above = [(s, r) for s, r in ranked if s >= _LIVE_THRESHOLD]
    if len(above) < _MIN_RESULTS:
        above = ranked[:_MIN_RESULTS]
    return [r for _, r in above[:top_k]]
