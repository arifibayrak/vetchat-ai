"""
Tests for ingestion: chunker, mock seeding, idempotency, missing API key.
Does not require any real API keys.
"""
import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import chromadb
import pytest
import tiktoken

from app.config import Settings
from app.ingestion.chunker import chunk_text, TARGET_TOKENS
from app.ingestion.pipeline import seed_mock
from app.ingestion.sciencedirect_client import ConfigurationError, ScienceDirectClient

_TOKENIZER = tiktoken.get_encoding("cl100k_base")


# ─── Chunker tests ────────────────────────────────────────────────────────────

def test_chunker_respects_token_budget():
    long_text = (
        "Xylitol is a sugar alcohol used as a sweetener. "
        "Dogs ingesting xylitol may develop hypoglycemia. "
        "The toxic dose is as low as 0.1 g/kg. "
        "Clinical signs include vomiting, ataxia, and seizures. "
    ) * 30  # ~600 tokens

    chunks = chunk_text(long_text)
    assert len(chunks) >= 1
    for chunk in chunks:
        n_tokens = len(_TOKENIZER.encode(chunk))
        # Allow slight overage from sentence-boundary rounding
        assert n_tokens <= TARGET_TOKENS + 50, f"Chunk exceeds token budget: {n_tokens}"


def test_chunker_returns_list_of_strings():
    chunks = chunk_text("This is a short text. It has two sentences.")
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)


def test_chunker_overlap_exists():
    """Adjacent chunks should share some content from the overlap window."""
    long_text = ". ".join([f"Sentence number {i} about veterinary medicine topics" for i in range(80)])
    chunks = chunk_text(long_text)
    if len(chunks) > 1:
        # The end of chunk 0 and start of chunk 1 should share some tokens
        end_of_first = chunks[0][-100:]
        start_of_second = chunks[1][:100]
        # Some words should appear in both
        words_first = set(end_of_first.lower().split())
        words_second = set(start_of_second.lower().split())
        overlap_words = words_first & words_second
        assert len(overlap_words) > 0, "Expected overlap between adjacent chunks"


# ─── Mock seed tests ──────────────────────────────────────────────────────────

@pytest.fixture
def in_memory_collection():
    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(
        name="test_vet_literature",
        metadata={"hnsw:space": "cosine"},
    )
    return collection


@pytest.fixture
def offline_settings():
    return Settings(anthropic_api_key="test-key", sciencedirect_api_key="")


def test_mock_seed_populates_chroma(in_memory_collection, offline_settings):
    n = asyncio.run(seed_mock(in_memory_collection, offline_settings))
    assert n > 0, "seed_mock should upsert at least one chunk"
    assert in_memory_collection.count() > 0


def test_mock_seed_is_idempotent(in_memory_collection, offline_settings):
    asyncio.run(seed_mock(in_memory_collection, offline_settings))
    count_after_first = in_memory_collection.count()
    asyncio.run(seed_mock(in_memory_collection, offline_settings))
    count_after_second = in_memory_collection.count()
    assert count_after_first == count_after_second, "Upsert should be idempotent"


def test_mock_chunks_have_required_metadata(in_memory_collection, offline_settings):
    asyncio.run(seed_mock(in_memory_collection, offline_settings))
    results = in_memory_collection.get(limit=5, include=["metadatas"])
    for meta in results["metadatas"]:
        assert "doi" in meta
        assert "title" in meta
        assert "journal" in meta
        assert "year" in meta


def test_mock_jsonl_files_are_valid_json():
    mock_dir = Path(__file__).parent.parent / "data" / "mock"
    for jsonl_file in mock_dir.glob("*.jsonl"):
        with open(jsonl_file) as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    record = json.loads(line)  # should not raise
                    assert "id" in record
                    assert "text" in record
                    assert "metadata" in record


# ─── ScienceDirect client: missing API key ────────────────────────────────────

def test_missing_sciencedirect_key_raises_configuration_error():
    with pytest.raises(ConfigurationError):
        ScienceDirectClient(api_key="")


def test_sciencedirect_client_with_key_instantiates():
    client = ScienceDirectClient(api_key="fake-key-for-instantiation-test")
    assert client is not None


def test_sciencedirect_client_handles_429(tmp_path):
    """Client should not crash on HTTP 429; should raise after retries."""
    import httpx
    from unittest.mock import patch

    client = ScienceDirectClient(api_key="fake-key")

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429", request=MagicMock(), response=mock_response
    )

    with patch("httpx.Client.get", side_effect=httpx.HTTPStatusError("429", request=MagicMock(), response=mock_response)):
        result = client.fetch_fulltext("10.1016/fake.doi")
        # 429 is treated as None (not available) per client logic
        assert result is None
