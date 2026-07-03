import { describe, expect, it, vi } from 'vitest';
import {
  capitalize,
  calculateReadingTime,
  cn,
  debounce,
  formatBytes,
  formatDate,
  formatNumber,
  generateId,
  getInitials,
  isEmpty,
  sleep,
  throttle,
  truncate,
} from '../../src/shared/lib/utils';

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('removes conflicting Tailwind classes (last wins)', () => {
    const result = cn('p-4', 'p-8');
    expect(result).toBe('p-8');
  });

  it('handles falsy values', () => {
    expect(cn('foo', false, undefined, null, 'bar')).toBe('foo bar');
  });
});

describe('formatNumber', () => {
  it('adds comma separators', () => {
    expect(formatNumber(1000)).toBe('1,000');
    expect(formatNumber(1000000)).toBe('1,000,000');
  });

  it('handles small numbers without commas', () => {
    expect(formatNumber(999)).toBe('999');
  });
});

describe('formatDate', () => {
  it('formats a Date object', () => {
    const result = formatDate(new Date('2024-03-15'));
    expect(result).toContain('2024');
    expect(result).toContain('March');
  });

  it('accepts an ISO string', () => {
    const result = formatDate('2024-01-01');
    expect(result).toContain('2024');
  });
});

describe('truncate', () => {
  it('truncates long text with ellipsis', () => {
    expect(truncate('Hello World', 5)).toBe('Hello...');
  });

  it('returns unchanged text when within limit', () => {
    expect(truncate('Hi', 10)).toBe('Hi');
  });

  it('returns unchanged text at exact limit', () => {
    expect(truncate('Hello', 5)).toBe('Hello');
  });
});

describe('capitalize', () => {
  it('capitalizes each word', () => {
    expect(capitalize('hello world')).toBe('Hello World');
  });

  it('lowercases the rest of each word', () => {
    expect(capitalize('HELLO WORLD')).toBe('Hello World');
  });
});

describe('generateId', () => {
  it('returns a non-empty string', () => {
    const id = generateId();
    expect(typeof id).toBe('string');
    expect(id.length).toBeGreaterThan(0);
  });

  it('returns different values on consecutive calls', () => {
    const ids = new Set(Array.from({ length: 10 }, () => generateId()));
    expect(ids.size).toBeGreaterThan(1);
  });
});

describe('isEmpty', () => {
  it('returns true for null and undefined', () => {
    expect(isEmpty(null)).toBe(true);
    expect(isEmpty(undefined)).toBe(true);
  });

  it('returns true for empty string and whitespace', () => {
    expect(isEmpty('')).toBe(true);
    expect(isEmpty('   ')).toBe(true);
  });

  it('returns false for non-empty string', () => {
    expect(isEmpty('hi')).toBe(false);
  });

  it('returns true for empty array', () => {
    expect(isEmpty([])).toBe(true);
  });

  it('returns false for non-empty array', () => {
    expect(isEmpty([1])).toBe(false);
  });

  it('returns true for empty object', () => {
    expect(isEmpty({})).toBe(true);
  });

  it('returns false for non-empty object', () => {
    expect(isEmpty({ a: 1 })).toBe(false);
  });

  it('returns false for numbers', () => {
    expect(isEmpty(0)).toBe(false);
    expect(isEmpty(42)).toBe(false);
  });
});

describe('sleep', () => {
  it('resolves after the given delay', async () => {
    vi.useFakeTimers();
    const promise = sleep(100);
    vi.advanceTimersByTime(100);
    await promise;
    vi.useRealTimers();
  });
});

describe('formatBytes', () => {
  it('formats 0 bytes', () => {
    expect(formatBytes(0)).toBe('0 Bytes');
  });

  it('formats KB', () => {
    expect(formatBytes(1024)).toBe('1 KB');
  });

  it('formats MB', () => {
    expect(formatBytes(1024 * 1024)).toBe('1 MB');
  });

  it('respects decimal places', () => {
    expect(formatBytes(1500, 1)).toBe('1.5 KB');
  });
});

describe('getInitials', () => {
  it('returns two-letter initials from full name', () => {
    expect(getInitials('John Doe')).toBe('JD');
  });

  it('returns single character for single-word name', () => {
    expect(getInitials('Johannes')).toBe('J');
  });
});

describe('calculateReadingTime', () => {
  it('returns 1 minute for a short text', () => {
    const text = 'word '.repeat(150).trim();
    expect(calculateReadingTime(text)).toBe(1);
  });

  it('scales with word count', () => {
    const text = 'word '.repeat(400).trim();
    expect(calculateReadingTime(text)).toBe(2);
  });

  it('accepts custom words-per-minute', () => {
    const text = 'word '.repeat(100).trim();
    expect(calculateReadingTime(text, 100)).toBe(1);
  });
});

describe('debounce', () => {
  it('delays function execution', () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced();
    expect(fn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('cancels previous call when called again within window', () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced();
    debounced();
    debounced();
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});

describe('throttle', () => {
  it('calls function immediately on first invocation', () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const throttled = throttle(fn, 100);

    throttled();
    expect(fn).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('suppresses additional calls within the throttle window', () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const throttled = throttle(fn, 100);

    throttled();
    throttled();
    throttled();
    expect(fn).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});
