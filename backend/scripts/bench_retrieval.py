#!/usr/bin/env python
"""
Retrieval benchmark — runs 20 curated vet queries through the Chroma
retrieve + cross-encoder rerank pipeline and dumps a CSV with score
distributions per query.

Use this to:
  1. Establish a baseline before ingestion so we know how bad things are.
  2. Re-run after ingest_crossref_tf.py + ingest_crossref_tox.py to quantify
     the lift (e.g. "tox queries top-5 median rerank_score: -2.1 → +0.4").
  3. Tune DISTANCE_THRESHOLD (retriever.py), _CHROMA_THRESHOLD /
     _LIVE_THRESHOLD / _MIN_RESULTS (reranker.py) from observed distributions
     instead of hand-picked numbers.

Usage
-----
    cd backend
    python scripts/bench_retrieval.py --out bench_out.csv

Output columns: query_id, domain, query, rank, distance, rerank_score,
source_type, journal, year, title.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from app.config import Settings
from app.services.retriever import search as chroma_search
from app.services.reranker import rerank

_QUERIES_FILE = Path(__file__).parent.parent / "data" / "bench_queries.json"


def _load_queries() -> list[dict]:
    with open(_QUERIES_FILE) as f:
        return json.load(f)["queries"]


def _fetch_source_type(collection: chromadb.Collection, chunk_id: str) -> str:
    try:
        got = collection.get(ids=[chunk_id], include=["metadatas"])
        metas = got.get("metadatas") or []
        if metas and metas[0]:
            return (metas[0].get("source_type") or "").strip()
    except Exception:
        pass
    return ""


def run_bench(chroma_path: str, out_path: str, top_k: int, n_results_pre_rerank: int) -> None:
    os.environ.setdefault("ANTHROPIC_API_KEY", "offline-bench")
    settings = Settings()

    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )
    total = collection.count()
    print(f"Chroma path        : {chroma_path}")
    print(f"Collection size    : {total}")
    if total == 0:
        print("Collection is empty — nothing to benchmark.")
        return

    queries = _load_queries()
    print(f"Benchmark queries  : {len(queries)}")
    print(f"n_results pre-rerank: {n_results_pre_rerank}")
    print(f"top_k per query    : {top_k}")
    print()

    rows: list[dict] = []
    per_query_stats: list[tuple[str, str, list[float]]] = []

    for q in queries:
        qid = q["id"]
        domain = q["domain"]
        query = q["query"]

        raw = chroma_search(
            query,
            collection,
            n_results=n_results_pre_rerank,
            embedding_model=settings.embedding_model,
        )
        ranked = rerank(query, raw, top_k=top_k, use_reranker=settings.use_reranker)

        scores = [c.rerank_score for c in ranked]
        per_query_stats.append((qid, domain, scores))

        for rank, c in enumerate(ranked, 1):
            source_type = _fetch_source_type(collection, c.id)
            rows.append({
                "query_id":     qid,
                "domain":       domain,
                "query":        query,
                "rank":         rank,
                "distance":     round(c.distance, 4),
                "rerank_score": round(c.rerank_score, 4),
                "source_type":  source_type,
                "journal":      c.journal[:80],
                "year":         c.year,
                "title":        c.title[:140],
            })

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "query_id", "domain", "query", "rank",
                "distance", "rerank_score",
                "source_type", "journal", "year", "title",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows → {out_path}\n")
    print("── per-query top-k rerank summary ──")
    print(f"{'query_id':<22} {'domain':<12} {'n':>3}  {'median':>8}  {'max':>7}  {'min':>7}")
    for qid, domain, scores in per_query_stats:
        n = len(scores)
        med = statistics.median(scores) if scores else float("nan")
        mx = max(scores) if scores else float("nan")
        mn = min(scores) if scores else float("nan")
        print(f"{qid:<22} {domain:<12} {n:>3}  {med:>8.3f}  {mx:>7.3f}  {mn:>7.3f}")

    all_top1 = [s[0] for _, _, s in per_query_stats if s]
    if all_top1:
        print()
        print(f"Corpus-wide median of top-1 rerank_score: {statistics.median(all_top1):.3f}")
        print(f"Queries whose top-1 is < 0 (tangential-at-best): "
              f"{sum(1 for s in all_top1 if s < 0)} / {len(all_top1)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chroma-path", default=None)
    parser.add_argument("--out", default="bench_retrieval.csv")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--n-results", type=int, default=20,
                        help="n_results passed to chroma_search before rerank (matches chat.py default)")
    args = parser.parse_args()

    settings = Settings()
    chroma_path = args.chroma_path or settings.chroma_path
    run_bench(chroma_path, args.out, args.top_k, args.n_results)


if __name__ == "__main__":
    main()
