import type { QuestionType } from '@/types/thema';

export type SessionStatus = 'active' | 'completed';

export type FeedbackMode = 'immediate' | 'end' | 'never';

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
  feedback_mode: FeedbackMode;
  total_questions: number;
  current_index: number;
  correct_count: number | null;
  session_complete: boolean;
  question: SessionQuestion | null;
}

export interface SubmitAnswerRequest {
  question_id: string;
  selected: string[];
  response_time_seconds?: number;
}

export interface AnswerResult {
  is_correct: boolean | null;
  correct_answers: string[] | null;
  explanation: string | null;
  state: SessionState;
}

export interface SessionSummary {
  session_id: string;
  quiz_id: string | null;
  quiz_title: string | null;
  quiz_deleted: boolean;
  thema: string | null;
  total_questions: number;
  correct_answers: number;
  accuracy: number;
  total_time_seconds: number | null;
  status: SessionStatus;
}

export interface SessionReviewEntry {
  question_id: string;
  question_type: QuestionType;
  question_text: string;
  options: string[] | null;
  selected: string[];
  is_correct: boolean | null;
  correct_answers: string[] | null;
  explanation: string | null;
}

export interface SessionReview {
  summary: SessionSummary;
  feedback_mode: FeedbackMode;
  entries: SessionReviewEntry[];
}

export interface SessionPreferences {
  default_feedback_mode: FeedbackMode;
}

export interface SessionHistoryEntry {
  session_id: string;
  quiz_id: string | null;
  quiz_title: string | null;
  quiz_deleted: boolean;
  thema: string | null;
  status: SessionStatus;
  feedback_mode: FeedbackMode;
  total_questions: number;
  correct_answers: number;
  accuracy: number;
  started_at: string;
  total_time_seconds: number | null;
}

export interface SessionHistory {
  sessions: SessionHistoryEntry[];
}

export const FEEDBACK_MODES: readonly {
  value: FeedbackMode;
  label: string;
  description: string;
}[] = [
  {
    value: 'immediate',
    label: 'Instant',
    description: 'See the answer after each question',
  },
  {
    value: 'end',
    label: 'At the end',
    description: 'Review everything once you finish',
  },
  {
    value: 'never',
    label: 'Exam mode',
    description: 'Score only — answers stay hidden',
  },
];

const SCORE_BANDS: readonly { min: number; className: string }[] = [
  { min: 90, className: 'text-green-500' },
  { min: 75, className: 'text-lime-500' },
  { min: 60, className: 'text-yellow-500' },
  { min: 45, className: 'text-amber-500' },
  { min: 30, className: 'text-orange-500' },
  { min: 0, className: 'text-red-500' },
];

export function scoreColorClass(percent: number): string {
  const band = SCORE_BANDS.find(b => percent >= b.min);
  return band ? band.className : 'text-red-500';
}
