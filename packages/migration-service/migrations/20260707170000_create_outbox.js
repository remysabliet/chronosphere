/**
 * Transactional outbox: events that must never be lost (e.g. a recorded
 * answer that drives BKT) are inserted here in the same transaction as the
 * domain write. A relay polls unpublished rows in id order, publishes them
 * to the matching Redis stream (topic column), then stamps published_at.
 * BIGINT identity keeps relay ordering cheap and gap-tolerant.
 */
export async function up(knex) {
  await knex.schema.createTable('outbox', table => {
    table.bigIncrements('id').primary();
    table.text('topic').notNullable();
    table.jsonb('payload').notNullable();
    table.timestamp('created_at').notNullable().defaultTo(knex.fn.now());
    table.timestamp('published_at');
  });
  await knex.raw(`
    CREATE INDEX idx_outbox_unpublished ON outbox (id)
    WHERE published_at IS NULL
  `);
}

export async function down(knex) {
  await knex.schema.dropTable('outbox');
}
