'use server';

import type {
  AnswerResult,
  SessionState,
  SessionSummary,
  SubmitAnswerRequest,
} from '@/types/session';

import { getJSON, postJSON } from './api-client';

export async function startSessionAction(
  quizId: string
): Promise<SessionState> {
  return postJSON(`/v1/quizzes/${quizId}/sessions`, {});
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
