export interface CitationItem {
  ref: number;
  title: string;
  journal: string;
  year: number;
  doi: string;
  url: string;
  authors: string;
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
