/**
 * Workflow doc cleanup: Step 10 stores the current BKT mastery P(Ln) per
 * concept-Bloom pair. The doc previously referenced a nonexistent
 * user_concept_mastery table; concept_progress_tracker is its real home.
 */
export async function up(knex) {
  await knex.schema.alterTable('concept_progress_tracker', table => {
    table.float('p_ln');
  });
}

export async function down(knex) {
  await knex.schema.alterTable('concept_progress_tracker', table => {
    table.dropColumn('p_ln');
  });
}
