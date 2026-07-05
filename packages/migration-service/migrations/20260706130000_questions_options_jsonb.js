/**
 * `json` re-parses the stored text on every read; `jsonb` is binary and
 * indexable. Nothing here needs exact text preservation, so jsonb is strictly
 * better — cheap to fix now, before this column has billions of rows in it.
 */
export async function up(knex) {
  await knex.raw(
    'ALTER TABLE questions ALTER COLUMN options TYPE jsonb USING options::jsonb'
  );
}

export async function down(knex) {
  await knex.raw(
    'ALTER TABLE questions ALTER COLUMN options TYPE json USING options::json'
  );
}
