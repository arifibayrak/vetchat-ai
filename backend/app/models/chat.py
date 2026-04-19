from pydantic import BaseModel


class ChatTurn(BaseModel):
    role: str      # "user" | "assistant"
    content: str


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
    relevance: str = ""   # "high" | "moderate" | "tangential" — from cross-encoder rerank score
    # Clinician-friendly inferred fields — populated server-side from title/abstract/doc_type
    study_type: str = ""          # "Review" | "RCT" | "Case series" | "Retrospective" | "Guideline" | "Research article" | ""
    species_relevance: str = ""   # "Dogs" | "Cats" | "Dogs & cats" | "Equine" | "Avian" | "Mixed" | ""
    why_it_matters: str = ""      # One-line clinician summary of how this source supports the claim
    evidence_tier: str = ""       # "direct" | "review" | "guideline" | "weak" | "none" — maps to in-line tag


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    history: list[ChatTurn] = []
    # When non-empty, backend reuses these citations instead of re-running retrieval.
    # Frontend populates this from the parent assistant message on follow-ups.
    prior_citations: list[CitationItem] = []


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
    # Evidence provenance for the whole answer
    evidence_mode: str = "literature"     # "literature" | "consensus" | "partial" | "gap"
    # Non-null when a fallback path produced the answer — drives frontend recovery UI
    fallback_kind: str | None = None      # None | "no_retrieval" | "guard_blocked" | "timeout_partial"
    # Counts per evidence tier for the evidence-summary strip in the UI
    evidence_counts: dict = {}            # {"direct": 3, "review": 1, "guideline": 2, "weak": 0}
    # Retrieved-but-hidden refs for the "Retrieved but not used" collapsible
    hidden_references: list[CitationItem] = []
