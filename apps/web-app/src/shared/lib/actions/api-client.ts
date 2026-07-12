import { auth } from '@/lib/auth';

const BASE_URL = process.env.NEXT_PUBLIC_QUESTION_GEN_URL;

async function authHeaders(): Promise<Record<string, string>> {
  const session = await auth();
  if (!session?.idToken || session.error) {
    throw new Error('Not authenticated');
  }
  return { Authorization: `Bearer ${session.idToken}` };
}

async function parse<T>(res: Response): Promise<T> {
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

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: await authHeaders(),
  });
  return parse<T>(res);
}

async function bodyJSON<T>(
  method: 'POST' | 'PATCH',
  path: string,
  body: unknown
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify(body),
  });
  return parse<T>(res);
}

export function postJSON<T>(path: string, body: unknown): Promise<T> {
  return bodyJSON<T>('POST', path, body);
}

export function patchJSON<T>(path: string, body: unknown): Promise<T> {
  return bodyJSON<T>('PATCH', path, body);
}
