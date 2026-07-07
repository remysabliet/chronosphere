import { describe, expect, it, vi } from 'vitest';
import { createCognitoVerifier, verifyBearerToken } from '../../src/index.js';

describe('verifyBearerToken', () => {
  it('throws when Authorization header is undefined', async () => {
    const verifier = { verify: vi.fn() };
    await expect(
      verifyBearerToken(undefined, verifier as never)
    ).rejects.toThrow('Missing bearer token');
    expect(verifier.verify).not.toHaveBeenCalled();
  });

  it('throws when header does not start with Bearer', async () => {
    const verifier = { verify: vi.fn() };
    await expect(
      verifyBearerToken('Basic abc123', verifier as never)
    ).rejects.toThrow('Missing bearer token');
    expect(verifier.verify).not.toHaveBeenCalled();
  });

  it('calls verifier.verify with the extracted token', async () => {
    const claims = { sub: 'user-123', email: 'user@example.com' };
    const verifier = { verify: vi.fn().mockResolvedValue(claims) };
    const result = await verifyBearerToken(
      'Bearer my.jwt.token',
      verifier as never
    );
    expect(verifier.verify).toHaveBeenCalledWith('my.jwt.token');
    expect(result).toEqual(claims);
  });

  it('propagates errors thrown by verifier.verify', async () => {
    const verifier = {
      verify: vi.fn().mockRejectedValue(new Error('Token expired')),
    };
    await expect(
      verifyBearerToken('Bearer expired.token', verifier as never)
    ).rejects.toThrow('Token expired');
  });
});

describe('createCognitoVerifier', () => {
  it('returns an object with a verify method', () => {
    const verifier = createCognitoVerifier({
      userPoolId: 'us-east-1_TESTPOOL',
      clientId: 'test-client-id',
    });
    expect(typeof verifier.verify).toBe('function');
  });
});
