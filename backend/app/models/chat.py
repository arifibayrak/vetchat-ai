from pydantic import BaseModel


class ChatTurn(BaseModel):
    role: str      # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    history: list[ChatTurn] = []


class CitationItem(BaseModel):
    ref: int
    title: str
    journal: str
    year: int
    doi: str
    url: str
    authors: str
    abstract: str = ""
    relevant_quote: str = ""
    intext_passage: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doc_type: str = ""
    cited_by: int = 0
    # Provenance — shown in UI so vets know exactly which publisher/database each source is from
    publisher: str = ""   # e.g. "Taylor & Francis", "Elsevier", "Springer Nature"
    source: str = ""      # e.g. "Scopus", "Springer Nature", "Taylor & Francis", "Literature"


class LiveResourceItem(BaseModel):
    source: str       # "Scopus" | "Springer Nature"
    title: str
    journal: str
    year: int
    authors: str
    doi: str
    url: str
    abstract: str
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doc_type: str = ""
    cited_by: int = 0


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationItem]
    live_resources: list[LiveResourceItem] = []
    emergency: bool
    category: str | None = None
    matched_term: str | None = None
    resources: list[str] = []
    disclaimer: str
    retrieval_quality: str = "moderate"   # "strong" | "moderate" | "weak"
    total_sources: int = 0
    cited_count: int = 0
