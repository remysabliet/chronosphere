import type { NextRequest } from 'next/server';

import { authHeaders, BASE_URL } from '@/lib/actions/api-client';

// EventSource can't send an Authorization header, so the browser connects
// here (NextAuth cookie) and this handler attaches the bearer token before
// piping the backend's SSE stream through untouched.
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest): Promise<Response> {
  let headers: Record<string, string>;
  try {
    headers = await authHeaders();
  } catch {
    return new Response(null, { status: 401 });
  }

  const upstream = await fetch(`${BASE_URL}/v1/quizzes/events`, {
    headers: { ...headers, Accept: 'text/event-stream' },
    cache: 'no-store',
    // Forward the browser's disconnect so the backend releases its
    // subscription instead of streaming into the void.
    signal: request.signal,
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(null, { status: 502 });
  }

  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
    },
  });
}
