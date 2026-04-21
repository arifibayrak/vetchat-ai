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
# Live APIs: tightened to -1.0 after empirical QA (2026-04-21) showed the
# previous -2.0 + min-4 floor was dragging Scopus/Springer junk scored -5 to
# -8 into the panel on weak-retrieval tox queries (T1/T3/T4). Local Chroma
# is the backstop when live APIs have nothing relevant — letting junk
# through here only degraded the reference panel.
_LIVE_THRESHOLD = -1.0
# Min-results floor applies ONLY to Chroma rerank. Live API has no floor —
# if live can't score above -1.0 it's genuinely off-topic and should be
# dropped entirely. Chroma keeps the min-4 so the consensus-fallback path
# still has material when retrieval is sparse.
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


def _matches_boost_journal(journal: str, boost_journals: frozenset[str]) -> bool:
    """Substring match so minor title variations ('Journal of X, The') still hit."""
    if not journal or not boost_journals:
        return False
    if journal in boost_journals:
        return True
    lowered = journal.lower()
    return any(name.lower() in lowered for name in boost_journals)


def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    top_k: int = 5,
    use_reranker: bool = True,
    boost_journals: frozenset[str] | None = None,
    boost_amount: float = 0.3,
) -> list[RetrievedChunk]:
    """
    Rerank ChromaDB chunks. Attaches each chunk's cross-encoder score to
    `.rerank_score`. Filters below threshold with a min-4 fallback.

    When `boost_journals` is supplied, chunks published in those journals
    get `boost_amount` added to their rerank_score BEFORE filtering — this
    lets toxicology queries tilt the prior toward known-relevant outlets
    (JVECC, Clinical Toxicology, etc.) without discarding the reranker's
    judgement. Stored score reflects the boosted value so downstream
    filters (reference hygiene) see the same signal.
    """
    if not chunks:
        return []

    if use_reranker:
        model = _get_cross_encoder()
        if model is not None:
            pairs = [(query, chunk.text) for chunk in chunks]
            scores = model.predict(pairs)
            boosted: list[float] = []
            for chunk, score in zip(chunks, scores):
                s = float(score)
                if _matches_boost_journal(chunk.journal, boost_journals or frozenset()):
                    s += boost_amount
                chunk.rerank_score = s
                boosted.append(s)
            ranked = sorted(zip(boosted, chunks), key=lambda x: x[0], reverse=True)
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
    # No min-results floor for live: if nothing scores above _LIVE_THRESHOLD
    # we return nothing and let Chroma + consensus fallback cover the query.
    above = [(s, r) for s, r in ranked if s >= _LIVE_THRESHOLD]
    return [r for _, r in above[:top_k]]
