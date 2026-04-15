"""
Ingestion pipeline: fetch → chunk → embed → upsert to Chroma.
Also exposes seed_mock() for offline startup seeding.
"""
import hashlib
import json
from pathlib import Path

import chromadb

from app.config import Settings
from app.ingestion.chunker import chunk_text
from app.ingestion.embedder import embed_texts
from app.ingestion.sciencedirect_client import ArticleMetadata, ConfigurationError, ScienceDirectClient
from app.ingestion.springer_nature_client import SpringerNatureClient

_MOCK_DIR = Path(__file__).parent.parent.parent / "data" / "mock"
_TF_JOURNALS_FILE = Path(__file__).parent.parent.parent / "data" / "taylor_francis_journals.json"


def _tf_journal_id(title: str) -> str:
    import hashlib
    return "tf_" + hashlib.sha256(title.encode()).hexdigest()[:12]


def seed_taylor_francis(collection: chromadb.Collection, embedding_model: str = "all-MiniLM-L6-v2") -> int:
    """Seed T&F veterinary journal catalog into Chroma. Returns number of entries upserted."""
    if not _TF_JOURNALS_FILE.exists():
        return 0

    with open(_TF_JOURNALS_FILE) as f:
        data = json.load(f)

    journals = data.get("journals", [])
    if not journals:
        return 0

    texts = []
    for j in journals:
        parts = [f"Journal: {j['title']}"]
        if j.get("subtitle"):
            parts.append(f"Subtitle: {j['subtitle']}")
        parts.append("Publisher: Taylor & Francis (tandfonline.com)")
        if j.get("print_issn"):
            parts.append(f"Print ISSN: {j['print_issn']}")
        if j.get("online_issn"):
            parts.append(f"Online ISSN: {j['online_issn']}")
        if j.get("url"):
            parts.append(f"URL: {j['url']}")
        parts.append("Category: Veterinary Science and Animal Health")
        texts.append(" | ".join(parts))

    embeddings = embed_texts(texts, model_name=embedding_model)

    ids, docs, embs, metas = [], [], [], []
    for j, text, emb in zip(journals, texts, embeddings):
        ids.append(_tf_journal_id(j["title"]))
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
            "print_issn": j.get("print_issn", ""),
            "online_issn": j.get("online_issn", ""),
            "url": j.get("url", ""),
        })

    collection.upsert(ids=ids, documents=docs, embeddings=embs, metadatas=metas)
    return len(ids)


def _chunk_id(doi: str, chunk_index: int) -> str:
    raw = f"{doi}_{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def ingest_article(
    article: ArticleMetadata,
    collection: chromadb.Collection,
    embedding_model: str = "all-MiniLM-L6-v2",
) -> int:
    """Chunk, embed, and upsert one article. Returns number of chunks upserted."""
    text = article.fulltext or article.abstract
    if not text.strip():
        return 0

    chunks = chunk_text(text)
    embeddings = embed_texts(chunks, model_name=embedding_model)

    ids, docs, embs, metas = [], [], [], []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        ids.append(_chunk_id(article.doi, i))
        docs.append(chunk)
        embs.append(emb)
        metas.append({
            "doi": article.doi,
            "title": article.title,
            "journal": article.journal,
            "year": article.year,
            "authors": article.authors,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "source_type": article.source_type,
        })

    collection.upsert(ids=ids, documents=docs, embeddings=embs, metadatas=metas)
    return len(ids)


def run_ingestion(
    queries: list[str],
    collection: chromadb.Collection,
    settings: Settings,
    count: int = 25,
    sources: list[str] | None = None,
) -> dict:
    """
    Run ingestion from one or more sources for a list of queries.

    sources: list of "sciencedirect" | "springer" — defaults to all configured sources.
    """
    if sources is None:
        sources = []
        if settings.sciencedirect_api_key:
            sources.append("sciencedirect")
        if settings.springer_nature_api_key:
            sources.append("springer")

    if not sources:
        return {
            "articles_fetched": 0,
            "chunks_upserted": 0,
            "errors": ["No API keys configured. Set SCIENCEDIRECT_API_KEY or SPRINGER_NATURE_API_KEY in .env."],
        }

    total_articles = 0
    total_chunks = 0
    errors: list[str] = []

    # Build clients for requested sources
    sd_client = None
    sn_client = None
    if "sciencedirect" in sources and settings.sciencedirect_api_key:
        sd_client = ScienceDirectClient(settings.sciencedirect_api_key)
    if "springer" in sources and settings.springer_nature_api_key:
        sn_client = SpringerNatureClient(settings.springer_nature_api_key)

    for query in queries:
        # --- ScienceDirect ---
        if sd_client:
            try:
                articles = sd_client.search(query, count=count)
                for article in articles:
                    fulltext = sd_client.fetch_fulltext(article.doi)
                    if fulltext:
                        article.fulltext = fulltext
                        article.source_type = "fulltext"
                    else:
                        abstract = sd_client.fetch_abstract(article.doi)
                        if abstract:
                            article.abstract = abstract
                    n = ingest_article(article, collection, settings.embedding_model)
                    total_chunks += n
                    if n > 0:
                        total_articles += 1
            except Exception as exc:
                errors.append(f"[ScienceDirect] Query '{query}': {exc}")

        # --- Springer Nature ---
        if sn_client:
            try:
                articles = sn_client.search(query, count=count)
                for article in articles:
                    n = ingest_article(article, collection, settings.embedding_model)
                    total_chunks += n
                    if n > 0:
                        total_articles += 1
            except Exception as exc:
                errors.append(f"[SpringerNature] Query '{query}': {exc}")

    return {
        "articles_fetched": total_articles,
        "chunks_upserted": total_chunks,
        "errors": errors,
    }


async def seed_mock(collection: chromadb.Collection, settings: Settings) -> int:
    """Seed Chroma with mock JSONL data. Returns number of chunks upserted."""
    total = 0
    for jsonl_file in sorted(_MOCK_DIR.glob("*.jsonl")):
        with open(jsonl_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                article = ArticleMetadata(
                    doi=record["metadata"]["doi"],
                    title=record["metadata"]["title"],
                    journal=record["metadata"]["journal"],
                    year=record["metadata"]["year"],
                    authors=record["metadata"]["authors"],
                    abstract=record["text"],
                    source_type=record["metadata"]["source_type"],
                )
                # Use mock record's pre-assigned id to keep idempotency
                chunk_id = record["id"]
                emb = embed_texts([record["text"]], model_name=settings.embedding_model)[0]
                collection.upsert(
                    ids=[chunk_id],
                    documents=[record["text"]],
                    embeddings=[emb],
                    metadatas=[record["metadata"]],
                )
                total += 1
    return total
