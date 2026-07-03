export interface ThemaCandidate {
  rank: number;
  thema: string;
  domain: string;
  disambiguator: string;
  confidence: number;
  confirmation: string;
  topics: string[];
}

export interface ResolvedThema {
  status: 'resolved';
  extraction_id: string;
  thema: string;
  domain: string;
  topics: string[];
  confidence: number;
  confirmation: string;
  alternates: ThemaCandidate[];
}

export interface AmbiguousThema {
  status: 'ambiguous';
  extraction_id: string;
  candidates: ThemaCandidate[];
}

export interface UnresolvedThema {
  status: 'unresolved';
  extraction_id: string;
}

export type ThemaExtractionResult =
  | ResolvedThema
  | AmbiguousThema
  | UnresolvedThema;

export interface ThemaRequest {
  raw_user_input: string;
  content_body?: string;
}

export interface RefineRequest {
  clarification: string;
}

export interface ConfirmRequest {
  chosen_rank?: number;
}
