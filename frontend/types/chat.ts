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

export interface ChatResponse {
  answer: string;
  citations: CitationItem[];
  live_resources: LiveResourceItem[];
  emergency: boolean;
  category?: string;
  matched_term?: string;
  resources: string[];
  disclaimer: string;
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
}
