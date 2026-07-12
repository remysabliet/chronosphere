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
  /** True when no prior exposure is on file — the wizard must ask before BKT can seed. */
  exposure_required: boolean;
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

export type ExposureLevel = 'Unseen' | 'Recognized' | 'Practiced' | 'Mastered';

export interface ExposureRequest {
  exposure_level: ExposureLevel;
}

export interface ExposureResult {
  thema: string;
  exposure_level: ExposureLevel;
  p_l0: number;
  concepts_initialized: number;
}

export type QuestionType =
  | 'MCQ'
  | 'MCQMultiSelect'
  | 'TrueFalse'
  | 'FillInBlank';
