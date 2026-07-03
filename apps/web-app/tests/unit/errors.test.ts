import { describe, expect, it } from 'vitest';
import {
  isSessionExpiredError,
  toFriendlyErrorMessage,
} from '../../src/shared/lib/errors';

describe('isSessionExpiredError', () => {
  it.each([
    'Missing bearer token',
    'Invalid token',
    'Malformed token',
    'Unknown signing key',
    'Not authenticated',
  ])('returns true when message contains "%s"', msg => {
    expect(isSessionExpiredError(new Error(msg))).toBe(true);
    expect(isSessionExpiredError(msg)).toBe(true);
  });

  it('returns false for unrelated Error', () => {
    expect(isSessionExpiredError(new Error('Something else entirely'))).toBe(
      false
    );
  });

  it('handles non-Error non-string input', () => {
    expect(isSessionExpiredError({ message: 'Invalid token' })).toBe(false);
    expect(isSessionExpiredError(null)).toBe(false);
    expect(isSessionExpiredError(undefined)).toBe(false);
  });
});

describe('toFriendlyErrorMessage', () => {
  it('maps auth errors to session-expired copy', () => {
    expect(toFriendlyErrorMessage(new Error('Invalid token'))).toBe(
      'Your session expired. Please sign in again.'
    );
    expect(toFriendlyErrorMessage(new Error('Not authenticated'))).toBe(
      'Your session expired. Please sign in again.'
    );
  });

  it('maps "already confirmed" to friendly copy', () => {
    const msg = toFriendlyErrorMessage(
      new Error('This extraction has already been confirmed')
    );
    expect(msg).toBe('This quiz topic was already confirmed.');
  });

  it('maps "extraction was refined" to friendly copy', () => {
    const msg = toFriendlyErrorMessage(
      new Error('This extraction was refined')
    );
    expect(msg).toContain('already refined');
  });

  it('maps "already been refined" to friendly copy', () => {
    const msg = toFriendlyErrorMessage(
      new Error('This extraction has already been refined')
    );
    expect(msg).toContain('already refined');
  });

  it('maps Mistral/AI errors to AI-unavailable copy', () => {
    expect(toFriendlyErrorMessage(new Error('Mistral API error'))).toContain(
      'AI'
    );
    expect(toFriendlyErrorMessage(new Error('AI service failed'))).toContain(
      'AI'
    );
    expect(
      toFriendlyErrorMessage(new Error('Request failed with status 502'))
    ).toContain('AI');
    expect(
      toFriendlyErrorMessage(new Error('Request failed with status 503'))
    ).toContain('AI');
  });

  it('maps network errors to connection copy', () => {
    expect(toFriendlyErrorMessage(new Error('Failed to fetch'))).toContain(
      'Connection'
    );
    expect(
      toFriendlyErrorMessage(new Error('NetworkError occurred'))
    ).toContain('Connection');
  });

  it('maps 500 / Internal Server Error to generic copy', () => {
    expect(toFriendlyErrorMessage(new Error('status 500'))).toContain(
      'went wrong'
    );
    expect(
      toFriendlyErrorMessage(new Error('Internal Server Error'))
    ).toContain('went wrong');
    expect(toFriendlyErrorMessage(new Error(''))).toContain('went wrong');
  });

  it('returns the raw message for unknown errors', () => {
    expect(
      toFriendlyErrorMessage(new Error('something specific happened'))
    ).toBe('something specific happened');
  });

  it('handles string input', () => {
    expect(toFriendlyErrorMessage('Missing bearer token')).toBe(
      'Your session expired. Please sign in again.'
    );
  });

  it('handles non-Error objects by stringifying them', () => {
    const result = toFriendlyErrorMessage({ code: 404 });
    expect(typeof result).toBe('string');
  });
});
