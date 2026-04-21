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
    # Raw cross-encoder score — kept so the enrich() step can classify relevance
    # without re-running the reranker, and so downstream code (reference hygiene,
    # tox-journal boost) can filter on it directly.
    rerank_score: float = 0.0
    # Two-axis evidence model (populated by evidence_tagger.enrich):
    #   relevance: how directly this source answers the query
    #   strength : the study-design quality of the source itself
    # These replace the tangled single-tier evidence_tier field.
    relevance: str = ""   # "direct" | "related" | "background" | "tangential" | ""
    strength: str = ""    # "guideline" | "systematic_review" | "clinical_study" | "case_series" | "narrative_review" | "expert_consensus" | ""
    # Clinician-friendly display fields — populated server-side
    study_type: str = ""          # human-readable label: "Review" | "RCT" | "Case series" | ...
    species_relevance: str = ""   # "Dogs" | "Cats" | "Dogs & cats" | "Equine" | ...
    why_it_matters: str = ""      # one-line rationale tying this source to the specific claim


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
    # Counts along each evidence axis for the summary strip in the UI
    # {"relevance": {"direct": 3, "related": 2, ...}, "strength": {"clinical_study": 4, ...}}
    evidence_counts: dict = {}
    # Retrieved-but-hidden refs for the "Retrieved but not used" collapsible
    hidden_references: list[CitationItem] = []
