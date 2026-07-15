'use server';

import type {
  AnswerResult,
  FeedbackMode,
  SessionHistory,
  SessionPreferences,
  SessionReview,
  SessionState,
  SessionSummary,
  SubmitAnswerRequest,
} from '@/types/session';

import { getJSON, postJSON } from './api-client';

export async function startSessionAction(
  quizId: string,
  feedbackMode: FeedbackMode | null
): Promise<SessionState> {
  // null → backend uses (and keeps) the stored default; only an explicit
  // selector click persists a new one.
  return postJSON(`/v1/quizzes/${quizId}/sessions`, {
    feedback_mode: feedbackMode,
  });
}

export async function getSessionAction(
  sessionId: string
): Promise<SessionState> {
  return getJSON(`/v1/sessions/${sessionId}`);
}

export async function submitAnswerAction(
  sessionId: string,
  body: SubmitAnswerRequest
): Promise<AnswerResult> {
  return postJSON(`/v1/sessions/${sessionId}/answers`, body);
}

export async function getSessionSummaryAction(
  sessionId: string
): Promise<SessionSummary> {
  return getJSON(`/v1/sessions/${sessionId}/summary`);
}

export async function getSessionReviewAction(
  sessionId: string
): Promise<SessionReview> {
  return getJSON(`/v1/sessions/${sessionId}/review`);
}

export async function getSessionPreferencesAction(): Promise<SessionPreferences> {
  return getJSON('/v1/me/session-preferences');
}

export async function listSessionsAction(
  quizId?: string
): Promise<SessionHistory> {
  const query = quizId ? `?quiz_id=${quizId}` : '';
  return getJSON(`/v1/sessions${query}`);
}
