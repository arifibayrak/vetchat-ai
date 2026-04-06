from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None


class CitationItem(BaseModel):
    ref: int
    title: str
    journal: str
    year: int
    doi: str
    url: str
    authors: str
    abstract: str = ""


class LiveResourceItem(BaseModel):
    source: str       # "ScienceDirect" | "Springer Nature"
    title: str
    journal: str
    year: int
    authors: str
    doi: str
    url: str
    abstract: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationItem]
    live_resources: list[LiveResourceItem] = []
    emergency: bool
    category: str | None = None
    matched_term: str | None = None
    resources: list[str] = []   # emergency hotlines
    disclaimer: str
