/**
 * Queue seam shared across Memosphere's TypeScript services.
 *
 * Mirrors `memosphere_messaging` in `shared-python` — keep the two in sync.
 * Transport today is Redis Streams with consumer groups (ioredis satisfies
 * `StreamsClient` structurally); on AWS the same interface fronts SQS/SNS.
 * Topic conventions: `jobs:*` (one consumer group, retried work) and
 * `events:*` (fan-out — one group per consuming service).
 *
 * Delivery is at-least-once: a message is acked only after its handler
 * resolves, so handlers must be idempotent. Undecodable payloads move to
 * `<topic>.dlq` instead of poisoning the group.
 */

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type Payload = Record<string, JsonValue>;

export const PAYLOAD_FIELD = 'payload';

export interface Message {
  id: string;
  topic: string;
  payload: Payload;
}

export type MessageHandler = (message: Message) => Promise<void>;

/** [stream, [id, [field, value, ...]][]][] — ioredis XREADGROUP reply shape. */
export type StreamBatch = [string, [string, string[]][]][];

/**
 * The slice of an ioredis client this module uses — structural, so the real
 * client and test fakes both fit without a hard ioredis dependency here.
 */
export interface StreamsClient {
  xadd(
    key: string,
    id: '*',
    field: string,
    value: string
  ): Promise<string | null>;
  xgroup(
    subcommand: 'CREATE',
    key: string,
    group: string,
    id: string,
    mkstream: 'MKSTREAM'
  ): Promise<unknown>;
  xreadgroup(
    groupToken: 'GROUP',
    group: string,
    consumer: string,
    countToken: 'COUNT',
    count: number,
    blockToken: 'BLOCK',
    blockMs: number,
    streamsToken: 'STREAMS',
    key: string,
    id: '>'
  ): Promise<unknown>;
  xack(key: string, group: string, ...ids: string[]): Promise<number>;
}

export interface ConsumeOptions {
  topic: string;
  group: string;
  consumer: string;
  handler: MessageHandler;
  count?: number;
  blockMs?: number;
  onError?: (error: unknown, messageId: string) => void;
}

export interface Broker {
  publish(topic: string, payload: Payload): Promise<string>;
  ensureGroup(topic: string, group: string): Promise<void>;
  consumeOnce(options: ConsumeOptions): Promise<number>;
}

export class RedisStreamsBroker implements Broker {
  constructor(private readonly client: StreamsClient) {}

  async publish(topic: string, payload: Payload): Promise<string> {
    const id = await this.client.xadd(
      topic,
      '*',
      PAYLOAD_FIELD,
      JSON.stringify(payload)
    );
    if (id === null) {
      throw new Error(`XADD to ${topic} returned no id`);
    }
    return id;
  }

  async ensureGroup(topic: string, group: string): Promise<void> {
    // id "0" so a new group also sees messages published before it existed.
    try {
      await this.client.xgroup('CREATE', topic, group, '0', 'MKSTREAM');
    } catch (error) {
      if (!(error instanceof Error) || !error.message.includes('BUSYGROUP')) {
        throw error;
      }
    }
  }

  async consumeOnce(options: ConsumeOptions): Promise<number> {
    const {
      topic,
      group,
      consumer,
      handler,
      count = 10,
      blockMs = 5000,
    } = options;
    const reply = (await this.client.xreadgroup(
      'GROUP',
      group,
      consumer,
      'COUNT',
      count,
      'BLOCK',
      blockMs,
      'STREAMS',
      topic,
      '>'
    )) as StreamBatch | null;
    if (!reply) {
      return 0;
    }
    let processed = 0;
    for (const [, entries] of reply) {
      for (const [messageId, fields] of entries) {
        const payload = decodePayload(fields);
        if (payload === null) {
          await this.deadLetter(topic, group, messageId, fields);
          continue;
        }
        try {
          await handler({ id: messageId, topic, payload });
        } catch (error) {
          // No ack: stays pending for redelivery/claiming.
          options.onError?.(error, messageId);
          continue;
        }
        await this.client.xack(topic, group, messageId);
        processed += 1;
      }
    }
    return processed;
  }

  private async deadLetter(
    topic: string,
    group: string,
    messageId: string,
    fields: string[]
  ): Promise<void> {
    const raw = fieldValue(fields, PAYLOAD_FIELD) ?? '';
    await this.client.xadd(`${topic}.dlq`, '*', PAYLOAD_FIELD, raw);
    await this.client.xack(topic, group, messageId);
  }
}

function fieldValue(fields: string[], name: string): string | undefined {
  for (let i = 0; i + 1 < fields.length; i += 2) {
    if (fields[i] === name) {
      return fields[i + 1];
    }
  }
  return undefined;
}

function decodePayload(fields: string[]): Payload | null {
  const raw = fieldValue(fields, PAYLOAD_FIELD);
  if (raw === undefined) {
    return null;
  }
  let decoded: JsonValue;
  try {
    decoded = JSON.parse(raw) as JsonValue;
  } catch {
    return null;
  }
  if (
    decoded === null ||
    typeof decoded !== 'object' ||
    Array.isArray(decoded)
  ) {
    return null;
  }
  return decoded;
}
