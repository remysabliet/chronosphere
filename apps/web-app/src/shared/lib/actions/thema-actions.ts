'use server';

import type {
  ConfirmRequest,
  ExposureRequest,
  ExposureResult,
  QuizLengthInterpretation,
  RefineRequest,
  ResolvedThema,
  ThemaExtractionResult,
  ThemaRequest,
} from '@/types/thema';

import { postJSON } from './api-client';

export async function extractThemaAction(
  body: ThemaRequest
): Promise<ThemaExtractionResult> {
  return postJSON('/v1/thema/extract', body);
}

export async function refineThemaAction(
  extractionId: string,
  body: RefineRequest
): Promise<ThemaExtractionResult> {
  return postJSON(`/v1/thema/${extractionId}/refine`, body);
}

export async function confirmThemaAction(
  extractionId: string,
  body: ConfirmRequest
): Promise<ResolvedThema> {
  return postJSON(`/v1/thema/${extractionId}/confirm`, body);
}

export async function submitExposureAction(
  extractionId: string,
  body: ExposureRequest
): Promise<ExposureResult> {
  return postJSON(`/v1/thema/${extractionId}/exposure`, body);
}

export async function interpretQuizLengthAction(
  rawUserInput: string
): Promise<QuizLengthInterpretation> {
  return postJSON('/v1/wizard/quiz-length/interpret', {
    raw_user_input: rawUserInput,
  });
}
