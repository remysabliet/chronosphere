import { afterAll, describe, expect, it } from 'vitest';
import request from 'supertest';
import { server } from '../../src/index.js';

afterAll(() => server.close());

describe('Content Management Service', () => {
  it('GET /health returns 200 with ok status', async () => {
    const res = await request(server).get('/health');
    expect(res.status).toBe(200);
    expect(res.body.status).toBe('ok');
    expect(res.body.service).toBe('content-management');
  });

  it('GET / returns 200 with service message', async () => {
    const res = await request(server).get('/');
    expect(res.status).toBe(200);
    expect(res.body.message).toContain('Content Management Service');
    expect(res.body.endpoints.health).toBe('/health');
  });

  it('GET /unknown returns 200 with default message', async () => {
    const res = await request(server).get('/unknown-path');
    expect(res.status).toBe(200);
    expect(res.body.message).toBeDefined();
  });
});
