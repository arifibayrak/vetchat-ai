"""
Shared test fixtures.
Chat endpoint now uses live APIs only — Chroma is only needed for the ingest tests.
All Claude and live-search calls are mocked; no real API keys are required.
"""
import asyncio
import os

import chromadb
import pytest
from fastapi.testclient import TestClient

# Pre-set env vars BEFORE importing any app modules
os.environ.setdefault("ANTHROPIC_API_KEY", "test-sk-fake-key-12345")
os.environ.setdefault("SCIENCEDIRECT_API_KEY", "test-sd-key")
os.environ.setdefault("SPRINGER_NATURE_API_KEY", "test-sn-key")
os.environ.setdefault("USE_MOCK_DATA", "false")
os.environ.setdefault("USE_RERANKER", "false")


@pytest.fixture(scope="session")
def test_client():
    """FastAPI TestClient with fake API keys; no Chroma needed for chat."""
    from app import config as cfg_module
    from app.config import Settings

    test_settings = Settings(
        anthropic_api_key="test-sk-fake-key-12345",
        sciencedirect_api_key="test-sd-key",
        springer_nature_api_key="test-sn-key",
        use_mock_data=False,
        use_reranker=False,
    )
    cfg_module._settings = test_settings

    from app.main import app

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


@pytest.fixture(scope="session")
def mock_collection():
    """In-memory Chroma pre-seeded with mock data — used by ingestion tests only."""
    client = chromadb.EphemeralClient()
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )
    from app.config import Settings
    from app.ingestion.pipeline import seed_mock
    settings = Settings(anthropic_api_key="test-sk-fake-key-12345")
    asyncio.run(seed_mock(collection, settings))
    return collection


@pytest.fixture(scope="session")
def empty_collection():
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection(name="vet_empty")
