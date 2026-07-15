import type { QuestionType } from '@/types/thema';

export type QuizVisibility = 'private' | 'shared' | 'public';
export type QuizScope = 'mine' | 'shared';
export type QuizStatus = 'ready' | 'generating';

export interface QuizCreateRequest {
  thema: string;
  title?: string;
  question_types: QuestionType[];
  question_count?: number;
  time_limit_minutes?: number;
  visibility?: QuizVisibility;
}

export interface QuizUpdateRequest {
  title: string;
}

export interface QuizResponse {
  id: string;
  thema: string;
  title: string;
  question_types: QuestionType[];
  question_count: number | null;
  time_limit_minutes: number | null;
  visibility: QuizVisibility;
  generation_batches_enqueued: number;
}

export interface QuizProgress {
  /** Informational count of questions produced so far. */
  questions_ready: number;
  questions_expected: number;
  /** Completion signal + progress source: ready once completed >= total. */
  jobs_completed: number;
  jobs_total: number;
  status: QuizStatus;
}

export function quizProgressPercent(progress: QuizProgress): number {
  return progress.jobs_total > 0
    ? Math.min(
        100,
        Math.round((progress.jobs_completed / progress.jobs_total) * 100)
      )
    : 0;
}

/** One generation-progress push from GET /api/quiz-events (SSE). */
export interface QuizProgressEvent extends QuizProgress {
  quiz_id: string;
}

export interface QuizListItem extends QuizProgress {
  id: string;
  thema: string;
  title: string;
  question_types: QuestionType[];
  question_count: number | null;
  time_limit_minutes: number | null;
  visibility: QuizVisibility;
  /** Distinct topics of the concepts this quiz was generated for. */
  topics: string[];
  /** Populated only when listed under scope='shared'. */
  owner_name: string | null;
  /** Drives owner-only UI (delete/rename) vs "Save to my quizzes". */
  is_owner: boolean;
  created_at: string;
  updated_at: string;
}

export interface QuizListResponse {
  items: QuizListItem[];
  has_more: boolean;
}

export interface QuizDetailResponse extends QuizProgress {
  id: string;
  thema: string;
  title: string;
  question_types: QuestionType[];
  question_count: number | null;
  time_limit_minutes: number | null;
  visibility: QuizVisibility;
  topics: string[];
  owner_name: string | null;
  /** Drives owner-only UI (delete/rename) vs "Save to my quizzes". */
  is_owner: boolean;
  created_at: string;
  updated_at: string;
}
