import { describe, expect, it } from 'vitest';

import {
  PAYLOAD_FIELD,
  RedisStreamsBroker,
  type Message,
  type StreamBatch,
  type StreamsClient,
} from '../../src/messaging';

class FakeStreams implements StreamsClient {
  added: Array<{ key: string; field: string; value: string }> = [];
  acked: Array<{ key: string; group: string; ids: string[] }> = [];
  groups: Array<{ key: string; group: string; id: string }> = [];
  constructor(
    private readonly batch: StreamBatch | null = null,
    private readonly groupError: string | null = null
  ) {}

  xadd(
    key: string,
    _id: '*',
    field: string,
    value: string
  ): Promise<string | null> {
    this.added.push({ key, field, value });
    return Promise.resolve(`${this.added.length}-0`);
  }

  xgroup(
    _sub: 'CREATE',
    key: string,
    group: string,
    id: string,
    _mkstream: 'MKSTREAM'
  ): Promise<unknown> {
    if (this.groupError !== null) {
      return Promise.reject(new Error(this.groupError));
    }
    this.groups.push({ key, group, id });
    return Promise.resolve('OK');
  }

  xreadgroup(): Promise<unknown> {
    return Promise.resolve(this.batch);
  }

  xack(key: string, group: string, ...ids: string[]): Promise<number> {
    this.acked.push({ key, group, ids });
    return Promise.resolve(ids.length);
  }
}

const entry = (id: string, raw: string): [string, string[]] => [
  id,
  [PAYLOAD_FIELD, raw],
];

describe('RedisStreamsBroker', () => {
  it('publishes the payload as JSON on the topic stream', async () => {
    const client = new FakeStreams();
    const broker = new RedisStreamsBroker(client);

    const id = await broker.publish('jobs:generate-questions', {
      quizId: 'q1',
      n: 5,
    });

    expect(id).toBe('1-0');
    expect(client.added[0].key).toBe('jobs:generate-questions');
    expect(JSON.parse(client.added[0].value)).toEqual({ quizId: 'q1', n: 5 });
  });

  it('creates the group from id 0 with MKSTREAM', async () => {
    const client = new FakeStreams();
    await new RedisStreamsBroker(client).ensureGroup(
      'events:response.recorded',
      'learning-engine'
    );

    expect(client.groups).toEqual([
      { key: 'events:response.recorded', group: 'learning-engine', id: '0' },
    ]);
  });

  it('swallows BUSYGROUP but rethrows other group errors', async () => {
    await expect(
      new RedisStreamsBroker(
        new FakeStreams(null, 'BUSYGROUP already exists')
      ).ensureGroup('events:x', 'g')
    ).resolves.toBeUndefined();

    await expect(
      new RedisStreamsBroker(
        new FakeStreams(null, 'connection refused')
      ).ensureGroup('events:x', 'g')
    ).rejects.toThrow('connection refused');
  });

  it('dispatches decoded messages and acks them', async () => {
    const batch: StreamBatch = [
      ['events:x', [entry('1-0', JSON.stringify({ a: 1 }))]],
    ];
    const client = new FakeStreams(batch);
    const broker = new RedisStreamsBroker(client);
    const seen: Message[] = [];

    const processed = await broker.consumeOnce({
      topic: 'events:x',
      group: 'g',
      consumer: 'c1',
      handler: message => {
        seen.push(message);
        return Promise.resolve();
      },
    });

    expect(processed).toBe(1);
    expect(seen[0].payload).toEqual({ a: 1 });
    expect(client.acked).toEqual([
      { key: 'events:x', group: 'g', ids: ['1-0'] },
    ]);
  });

  it('returns zero on an empty poll', async () => {
    const broker = new RedisStreamsBroker(new FakeStreams(null));
    const processed = await broker.consumeOnce({
      topic: 'events:x',
      group: 'g',
      consumer: 'c1',
      handler: () => Promise.reject(new Error('should not be called')),
    });
    expect(processed).toBe(0);
  });

  it('leaves failed messages pending and keeps processing the batch', async () => {
    const batch: StreamBatch = [
      [
        'events:x',
        [
          entry('1-0', JSON.stringify({ ok: false })),
          entry('2-0', JSON.stringify({ ok: true })),
        ],
      ],
    ];
    const client = new FakeStreams(batch);
    const errors: string[] = [];

    const processed = await new RedisStreamsBroker(client).consumeOnce({
      topic: 'events:x',
      group: 'g',
      consumer: 'c1',
      handler: message =>
        message.payload.ok === false
          ? Promise.reject(new Error('boom'))
          : Promise.resolve(),
      onError: (_error, messageId) => {
        errors.push(messageId);
      },
    });

    expect(processed).toBe(1);
    expect(errors).toEqual(['1-0']);
    expect(client.acked).toEqual([
      { key: 'events:x', group: 'g', ids: ['2-0'] },
    ]);
  });

  it.each(['not json', JSON.stringify([1, 2]), JSON.stringify('str')])(
    'dead-letters undecodable payload %#',
    async raw => {
      const batch: StreamBatch = [['events:x', [entry('1-0', raw)]]];
      const client = new FakeStreams(batch);

      const processed = await new RedisStreamsBroker(client).consumeOnce({
        topic: 'events:x',
        group: 'g',
        consumer: 'c1',
        handler: () => Promise.reject(new Error('should not be called')),
      });

      expect(processed).toBe(0);
      expect(client.added).toEqual([
        { key: 'events:x.dlq', field: PAYLOAD_FIELD, value: raw },
      ]);
      expect(client.acked).toEqual([
        { key: 'events:x', group: 'g', ids: ['1-0'] },
      ]);
    }
  );
});
