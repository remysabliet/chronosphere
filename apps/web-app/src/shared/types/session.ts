import type { QuestionType } from '@/types/thema';

export type SessionStatus = 'active' | 'completed';

export interface SessionQuestion {
  id: string;
  question_type: QuestionType;
  question_text: string;
  options: string[] | null;
  estimated_time_seconds: number | null;
}

export interface SessionState {
  session_id: string;
  quiz_id: string | null;
  total_questions: number;
  current_index: number;
  correct_count: number;
  session_complete: boolean;
  question: SessionQuestion | null;
}

export interface SubmitAnswerRequest {
  question_id: string;
  selected: string[];
  response_time_seconds?: number;
}

export interface AnswerResult {
  is_correct: boolean;
  correct_answers: string[];
  explanation: string;
  state: SessionState;
}

export interface SessionSummary {
  session_id: string;
  quiz_id: string | null;
  total_questions: number;
  correct_answers: number;
  accuracy: number;
  total_time_seconds: number | null;
  status: SessionStatus;
}
