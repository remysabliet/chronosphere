'use server';

import type {
  QuizCreateRequest,
  QuizDetailResponse,
  QuizListResponse,
  QuizScope,
  QuizStatus,
  QuizResponse,
} from '@/types/quiz';

import { getJSON, patchJSON, postJSON } from './api-client';

export async function createQuizAction(
  body: QuizCreateRequest
): Promise<QuizResponse> {
  return postJSON('/v1/quizzes', body);
}

export interface ListQuizzesParams {
  scope: QuizScope;
  q?: string;
  status?: QuizStatus;
  page?: number;
}

export async function listQuizzesAction(
  params: ListQuizzesParams
): Promise<QuizListResponse> {
  const search = new URLSearchParams({ scope: params.scope });
  if (params.q) search.set('q', params.q);
  if (params.status) search.set('status', params.status);
  if (params.page) search.set('page', String(params.page));
  return getJSON(`/v1/quizzes?${search.toString()}`);
}

export async function getQuizAction(id: string): Promise<QuizDetailResponse> {
  return getJSON(`/v1/quizzes/${id}`);
}

export async function renameQuizAction(
  id: string,
  title: string
): Promise<QuizDetailResponse> {
  return patchJSON(`/v1/quizzes/${id}`, { title });
}
