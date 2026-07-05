/**
 * Adaptive engine review point 2: BKT P(Ln) is the single learner mastery
 * signal; the per-concept IRT ability score (theta) is removed.
 */
export async function up(knex) {
  await knex.schema.alterTable('mastery_log', table => {
    table.dropColumn('theta_at_mastery');
  });
}

export async function down(knex) {
  await knex.schema.alterTable('mastery_log', table => {
    table.float('theta_at_mastery').notNullable().defaultTo(0);
  });
}
