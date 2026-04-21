export type FlowStep =
  | { type: "node"; text: string; sub?: string; highlight?: boolean }
  | { type: "branch"; items: string[] }
  | { type: "note"; text: string };

export interface FlowData {
  title: string;
  icon: string;
  steps: FlowStep[];
  source: string;
}

export type RelevanceAxis = "direct" | "related" | "background" | "tangential" | "";
export type StrengthAxis =
  | "guideline"
  | "systematic_review"
  | "clinical_study"
  | "case_series"
  | "narrative_review"
  | "expert_consensus"
  | "";

export interface CitationItem {
  ref: number;
  title: string;
  journal: string;
  year: number;
  doi: string;
  url: string;
  authors: string;
  abstract?: string;
  relevant_quote?: string;
  intext_passage?: string;
  volume?: string;
  issue?: string;
  pages?: string;
  doc_type?: string;
  cited_by?: number;
  // Provenance — which publisher/database this source came from
  publisher?: string;
  source?: string;
  rerank_score?: number;
  // Two-axis evidence model (server-side, via evidence_tagger):
  //   relevance — how directly the source answers the query
  //   strength  — the study-design quality of the source
  relevance?: RelevanceAxis;
  strength?: StrengthAxis;
  // Clinician-friendly display fields
  study_type?: string;          // human-readable: "Review" | "RCT" | "Case series" | ...
  species_relevance?: string;   // "Dogs" | "Cats" | "Dogs & cats" | "Equine" | ...
  why_it_matters?: string;      // one-line rationale tying this source to the specific claim
}

export interface LiveResourceItem {
  source: string;
  title: string;
  journal: string;
  year: number;
  authors: string;
  doi: string;
  url: string;
  abstract: string;
  volume?: string;
  issue?: string;
  pages?: string;
  doc_type?: string;
  cited_by?: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  clinic?: string;
  country?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface EmergencyPreliminary {
  category: string;
  heading: string;
  priorities: string[];
}

export type EvidenceMode = "literature" | "consensus" | "partial" | "gap";
export type FallbackKind = "no_retrieval" | "guard_blocked" | "timeout_partial" | null;

// Counts along each evidence axis — backend sends both maps; frontend
// renders a two-row summary strip in ReferencesPanel.
export interface EvidenceCounts {
  relevance?: Partial<Record<Exclude<RelevanceAxis, "">, number>>;
  strength?: Partial<Record<Exclude<StrengthAxis, "">, number>>;
}

export interface ChatResponse {
  answer: string;
  citations: CitationItem[];
  live_resources: LiveResourceItem[];
  emergency: boolean;
  category?: string;
  matched_term?: string;
  resources: string[];
  disclaimer: string;
  flow?: FlowData;
  retrieval_quality?: "strong" | "moderate" | "weak";
  total_sources?: number;
  cited_count?: number;
  evidence_mode?: EvidenceMode;
  fallback_kind?: FallbackKind;
  evidence_counts?: EvidenceCounts;
  hidden_references?: CitationItem[];
}

export interface ProgressStep {
  step: number;
  label: string;
  icon: string;
  done: boolean;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: CitationItem[];
  liveResources: LiveResourceItem[];
  emergency: boolean;
  resources: string[];
  isLoading?: boolean;
  steps?: ProgressStep[];
  currentStep?: number;
  flow?: FlowData;
  emergencyPreliminary?: EmergencyPreliminary;
  retrievalQuality?: "strong" | "moderate" | "weak";
  totalSources?: number;
  citedCount?: number;
  isSlowQuery?: boolean;
  isStreaming?: boolean;
  evidenceMode?: EvidenceMode;
  fallbackKind?: FallbackKind;
  evidenceCounts?: EvidenceCounts;
  hiddenReferences?: CitationItem[];
  // Populated when the stream failed (network / 5xx / timeout) so the UI can
  // render a recoverable fallback bubble with Retry / Safe-summary actions
  // instead of silently removing the bubble.
  failureKind?: "network" | "timeout" | "server";
  failureMessage?: string;
  originalQuery?: string;
}
