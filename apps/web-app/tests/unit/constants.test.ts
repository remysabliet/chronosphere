import { describe, expect, it } from 'vitest';
import {
  APP_NAME,
  APP_DESCRIPTION,
  ROUTES,
  FEATURES,
  PRICING_TIERS,
  PAGINATION,
  TIMEOUTS,
  MAX_FILE_SIZE,
  ALLOWED_IMAGE_TYPES,
} from '../../src/shared/lib/constants';

describe('constants', () => {
  it('APP_NAME is Memosphere', () => {
    expect(APP_NAME).toBe('Memosphere');
  });

  it('APP_DESCRIPTION is defined', () => {
    expect(APP_DESCRIPTION).toBeTruthy();
  });

  it('ROUTES covers core paths', () => {
    expect(ROUTES.HOME).toBe('/');
    expect(ROUTES.LOGIN).toBe('/login');
    expect(ROUTES.DASHBOARD).toBe('/app/dashboard');
    expect(ROUTES.QUIZ_NEW).toBe('/app/quiz/new');
  });

  it('FEATURES is a non-empty array', () => {
    expect(Array.isArray(FEATURES)).toBe(true);
    expect(FEATURES.length).toBeGreaterThan(0);
    expect(FEATURES[0]).toHaveProperty('title');
    expect(FEATURES[0]).toHaveProperty('description');
  });

  it('PRICING_TIERS has exactly 3 tiers', () => {
    expect(PRICING_TIERS).toHaveLength(3);
    expect(PRICING_TIERS[0].name).toBe('Free');
    expect(PRICING_TIERS[1].name).toBe('Pro');
    expect(PRICING_TIERS[2].name).toBe('Enterprise');
  });

  it('PAGINATION defaults make sense', () => {
    expect(PAGINATION.DEFAULT_PAGE_SIZE).toBe(20);
    expect(PAGINATION.MAX_PAGE_SIZE).toBeGreaterThan(
      PAGINATION.DEFAULT_PAGE_SIZE
    );
  });

  it('TIMEOUTS are positive numbers', () => {
    expect(TIMEOUTS.TOAST).toBeGreaterThan(0);
    expect(TIMEOUTS.DEBOUNCE).toBeGreaterThan(0);
    expect(TIMEOUTS.THROTTLE).toBeGreaterThan(0);
  });

  it('MAX_FILE_SIZE is 10 MB', () => {
    expect(MAX_FILE_SIZE).toBe(10 * 1024 * 1024);
  });

  it('ALLOWED_IMAGE_TYPES includes jpeg and png', () => {
    expect(ALLOWED_IMAGE_TYPES).toContain('image/jpeg');
    expect(ALLOWED_IMAGE_TYPES).toContain('image/png');
  });
});
