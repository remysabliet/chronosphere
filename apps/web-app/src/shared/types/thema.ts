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

export type NonTopicKind =
  | 'greeting_or_chitchat'
  | 'meta_question'
  | 'unintelligible';

export interface NonTopicInput {
  status: 'non_topic';
  extraction_id: string;
  input_kind: NonTopicKind;
  /** In-character wizard reply from the model; may be empty. */
  reply: string;
}

export type ThemaExtractionResult =
  | ResolvedThema
  | AmbiguousThema
  | UnresolvedThema
  | NonTopicInput;

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

export interface QuizLengthInterpretation {
  minutes: number | null;
  question_count: number | null;
  unlimited: boolean;
  /** In-character wizard sentence; non-empty only when no size could be read. */
  reply: string;
}
