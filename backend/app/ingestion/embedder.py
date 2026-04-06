"""
Sentence-transformers embedding singleton.
Model: all-MiniLM-L6-v2 (384-dim, CPU-friendly, ~80MB).
"""
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def get_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    global _model
    if _model is None or _model.get_sentence_embedding_dimension() == 0:
        _model = SentenceTransformer(model_name)
    return _model


def embed_texts(texts: list[str], model_name: str = "all-MiniLM-L6-v2", batch_size: int = 32) -> list[list[float]]:
    """Embed a list of texts. Returns list of 384-dim float vectors."""
    model = get_model(model_name)
    embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
    return [e.tolist() for e in embeddings]
