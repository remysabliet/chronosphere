const AUTH_ERROR_MESSAGES = [
  'Missing bearer token',
  'Invalid token',
  'Malformed token',
  'Unknown signing key',
  'Not authenticated',
];

const FRIENDLY_MESSAGES: Record<string, string> = {
  'This extraction has already been confirmed':
    'This quiz topic was already confirmed.',
  'This extraction was refined':
    'That topic was already refined — try the latest version.',
  'This extraction has already been refined':
    'That topic was already refined — try the latest version.',
};

export function isSessionExpiredError(error: unknown): boolean {
  const raw = error instanceof Error ? error.message : String(error);
  return AUTH_ERROR_MESSAGES.some(message => raw.includes(message));
}

/** Maps raw API/network errors to copy a learner can act on, instead of exposing backend internals. */
export function toFriendlyErrorMessage(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error);

  if (isSessionExpiredError(error)) {
    return 'Your session expired. Please sign in again.';
  }

  for (const [match, friendly] of Object.entries(FRIENDLY_MESSAGES)) {
    if (raw.includes(match)) {
      return friendly;
    }
  }

  if (
    raw.includes('Mistral') ||
    raw.includes('AI ') ||
    raw.includes('status 502') ||
    raw.includes('status 503')
  ) {
    return "We couldn't reach the AI right now. Please try again in a moment.";
  }

  if (raw.includes('Failed to fetch') || raw.includes('NetworkError')) {
    return 'Connection problem. Check your network and try again.';
  }

  if (
    !raw ||
    raw.includes('status 500') ||
    raw.includes('Internal Server Error')
  ) {
    return 'Something went wrong on our end. Please try again.';
  }

  return raw;
}
