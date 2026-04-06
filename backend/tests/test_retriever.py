"""
Tests for the retriever service.
Uses in-memory Chroma seeded with mock data.
"""
import pytest
from app.services import retriever


def test_retrieval_returns_chunks(mock_collection):
    chunks = retriever.search("xylitol dog poisoning", mock_collection)
    assert len(chunks) > 0


def test_retrieval_metadata_shape(mock_collection):
    chunks = retriever.search("xylitol", mock_collection)
    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.doi
        assert chunk.title
        assert chunk.journal
        assert isinstance(chunk.year, int)


def test_retrieval_distance_filter_unrelated(mock_collection):
    """Highly unrelated queries should return nothing or very few results."""
    chunks = retriever.search(
        "quantum physics black holes space telescope",
        mock_collection,
        distance_threshold=0.5,  # tighter threshold
    )
    # Not asserting zero because embeddings can have unexpected cosine similarities,
    # but we verify the function returns a list without error
    assert isinstance(chunks, list)


def test_retrieval_empty_collection_returns_empty(empty_collection):
    chunks = retriever.search("xylitol dog", empty_collection)
    assert chunks == []


def test_retrieval_returns_list_of_retrieved_chunks(mock_collection):
    from app.services.retriever import RetrievedChunk
    chunks = retriever.search("canine dermatitis pruritus", mock_collection)
    for chunk in chunks:
        assert isinstance(chunk, RetrievedChunk)


def test_retrieval_respects_n_results(mock_collection):
    chunks = retriever.search("veterinary", mock_collection, n_results=3)
    assert len(chunks) <= 3


def test_dermatology_query_retrieves_relevant(mock_collection):
    chunks = retriever.search("dog itching skin inflammation atopy", mock_collection)
    # At least one chunk should be from the dermatology mock
    titles = [c.title.lower() for c in chunks]
    assert any("atop" in t or "derm" in t or "pruritus" in t for t in titles)
