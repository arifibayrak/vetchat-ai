from pydantic import BaseModel


class IngestRequest(BaseModel):
    queries: list[str]
    count: int = 25
    sources: list[str] | None = None  # ["sciencedirect", "springer"] — None = all configured


class IngestResult(BaseModel):
    articles_fetched: int
    chunks_upserted: int
    queries_processed: list[str]
    errors: list[str] = []
