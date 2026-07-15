/**
 * Quiz "generating" completion was inferred from generation_questions_ready
 * reaching a target derived from the time limit (minutes*60/45). But the number
 * of questions a quiz can ever produce is jobs_enqueued * BATCH_SIZE minus the
 * questions each batch drops to validation/dedup — so any shortfall left the
 * quiz stuck in "generating" forever (e.g. 234/240). Completion now tracks the
 * jobs themselves: a quiz is done when every enqueued generation job has
 * finished, regardless of how many questions each yielded.
 *
 * - generation_jobs_total: set at creation to the number of jobs enqueued.
 * - generation_jobs_completed: incremented by the worker (once per job, in the
 *   same idempotent claim as generation_questions_ready).
 */
export async function up(knex) {
  await knex.schema.alterTable('quizzes', table => {
    table.integer('generation_jobs_total').notNullable().defaultTo(0);
    table.integer('generation_jobs_completed').notNullable().defaultTo(0);
  });

  // Backfill existing quizzes: jobs_total = the generation jobs enqueued for the
  // quiz (its outbox rows). Setting jobs_completed = jobs_total marks them all
  // done, which lifts quizzes wedged in the old questions-count heuristic out of
  // "generating". ASSUMPTION: no generation jobs are in flight when this runs
  // (true on the DB this was written against — zero pending stream entries).
  // If a job IS still in flight, its quiz flips to "ready" early with a partial
  // question pool; the DB can't detect in-flight Redis jobs, so this backfill
  // can't be made exact. The worker's completion increment is clamped with
  // LEAST(completed + 1, total) so a straggler completing afterwards can't push
  // jobs_completed past jobs_total.
  await knex.raw(`
    UPDATE quizzes q
    SET generation_jobs_total = sub.n,
        generation_jobs_completed = sub.n
    FROM (
      SELECT (payload->>'quiz_id')::uuid AS quiz_id, count(*) AS n
      FROM outbox
      WHERE topic = 'jobs:generate-questions'
        AND payload->>'quiz_id' IS NOT NULL
      GROUP BY payload->>'quiz_id'
    ) sub
    WHERE q.id = sub.quiz_id
  `);
}

export async function down(knex) {
  await knex.schema.alterTable('quizzes', table => {
    table.dropColumn('generation_jobs_total');
    table.dropColumn('generation_jobs_completed');
  });
}
