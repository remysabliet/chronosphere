'use server';

import { auth } from '@/lib/auth';
import type {
  ConfirmRequest,
  RefineRequest,
  ResolvedThema,
  ThemaExtractionResult,
  ThemaRequest,
} from '@/types/thema';

const BASE_URL = process.env.NEXT_PUBLIC_QUESTION_GEN_URL;

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const session = await auth();
  if (!session?.idToken || session.error) {
    throw new Error('Not authenticated');
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${session.idToken}`,
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item: { msg?: string }) => item.msg).join(', ')
      : detail;
    throw new Error(message || `Request failed with status ${res.status}`);
  }

  return res.json() as Promise<T>;
}

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
