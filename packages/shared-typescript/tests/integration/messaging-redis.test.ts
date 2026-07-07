/**
 * Drives RedisStreamsBroker through the real ioredis client against a live
 * Redis (the compose container). Skips cleanly when Redis is unreachable.
 */
import { Redis } from 'ioredis';
import { afterAll, describe, expect, it } from 'vitest';

import {
  PAYLOAD_FIELD,
  RedisStreamsBroker,
  type Message,
  type StreamsClient,
} from '../../src/messaging';

const REDIS_URL = process.env.REDIS_URL ?? 'redis://localhost:6379';

async function connect(): Promise<Redis | null> {
  const client = new Redis(REDIS_URL, {
    lazyConnect: true,
    connectTimeout: 1000,
    maxRetriesPerRequest: 0,
    retryStrategy: () => null,
  });
  try {
    await client.connect();
    await client.ping();
    return client;
  } catch {
    client.disconnect();
    return null;
  }
}

const client = await connect();

afterAll(() => {
  client?.disconnect();
});

describe.runIf(client !== null)('RedisStreamsBroker against real Redis', () => {
  const redis = (): Redis => {
    if (client === null) throw new Error('unreachable');
    return client;
  };
  const topicName = (): string => `itest:${crypto.randomUUID()}`;

  it('round-trips publish → consume through ioredis', async () => {
    const topic = topicName();
    const broker = new RedisStreamsBroker(redis() as StreamsClient);
    await broker.ensureGroup(topic, 'g0');
    await broker.ensureGroup(topic, 'g0'); // idempotent: real BUSYGROUP swallowed

    await broker.publish(topic, {
      quizId: 'q1',
      bucket: { bloom: 'Applying', n: 5 },
    });
    await broker.publish(topic, { quizId: 'q2', bucket: null });

    const seen: Message[] = [];
    const processed = await broker.consumeOnce({
      topic,
      group: 'g0',
      consumer: 'c1',
      blockMs: 100,
      handler: message => {
        seen.push(message);
        return Promise.resolve();
      },
    });

    expect(processed).toBe(2);
    expect(seen.map(m => m.payload)).toEqual([
      { quizId: 'q1', bucket: { bloom: 'Applying', n: 5 } },
      { quizId: 'q2', bucket: null },
    ]);
    const [pending] = (await redis().xpending(topic, 'g0')) as [
      number,
      ...unknown[],
    ];
    expect(pending).toBe(0);
    await redis().del(topic, `${topic}.dlq`);
  });

  it('leaves a failed message pending for redelivery', async () => {
    const topic = topicName();
    const broker = new RedisStreamsBroker(redis() as StreamsClient);
    await broker.ensureGroup(topic, 'g0');
    await broker.publish(topic, { will: 'fail' });

    const processed = await broker.consumeOnce({
      topic,
      group: 'g0',
      consumer: 'c1',
      blockMs: 100,
      handler: () => Promise.reject(new Error('boom')),
    });

    expect(processed).toBe(0);
    const [pending] = (await redis().xpending(topic, 'g0')) as [
      number,
      ...unknown[],
    ];
    expect(pending).toBe(1); // unacked → redeliverable via XAUTOCLAIM
    await redis().del(topic, `${topic}.dlq`);
  });

  it('dead-letters undecodable payloads', async () => {
    const topic = topicName();
    const broker = new RedisStreamsBroker(redis() as StreamsClient);
    await broker.ensureGroup(topic, 'g0');
    await redis().xadd(topic, '*', PAYLOAD_FIELD, 'not json');

    const processed = await broker.consumeOnce({
      topic,
      group: 'g0',
      consumer: 'c1',
      blockMs: 100,
      handler: () => Promise.reject(new Error('should not be called')),
    });

    expect(processed).toBe(0);
    expect(await redis().xlen(`${topic}.dlq`)).toBe(1);
    const [pending] = (await redis().xpending(topic, 'g0')) as [
      number,
      ...unknown[],
    ];
    expect(pending).toBe(0); // acked away from the group
    await redis().del(topic, `${topic}.dlq`);
  });
});
