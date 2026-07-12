/**
 * Records which learning-unit concepts a quiz was actually generated for
 * (one row per concept–bloom bucket enqueued in QuizService.create), so the
 * concepts/topics behind a quiz can be displayed and searched without
 * depending on outbox payloads or a session having started.
 */
export async function up(knex) {
  await knex.schema.createTable('quiz_concepts', table => {
    table.uuid('quiz_id').notNullable();
    table.uuid('concept_id').notNullable();
    table.primary(['quiz_id', 'concept_id']);

    table
      .foreign('quiz_id')
      .references('id')
      .inTable('quizzes')
      .onDelete('CASCADE');
    table
      .foreign('concept_id')
      .references('id')
      .inTable('learning_units')
      .onDelete('CASCADE');

    table.index(['concept_id']);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('quiz_concepts');
}
