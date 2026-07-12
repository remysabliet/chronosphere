/**
 * @param { import("knex").Knex } knex
 * @returns { Promise<void> }
 */
export const seed = async function (knex) {
  // TRUNCATE ... CASCADE (not .del()) so re-running this seed against a
  // database where learning_units already exists doesn't fail with a FK
  // violation on learning_units_complexity_level_foreign — CASCADE clears
  // those dependent rows too, and 003_learning_content re-inserts them.
  await knex.raw(
    'TRUNCATE TABLE bkt_parameter_defaults, bloom_level_weights, bloom_levels CASCADE'
  );

  // Insert BKT parameter defaults
  await knex('bkt_parameter_defaults').insert([
    { complexity_level: 'Low', P_T: 0.25, P_L0: 0.2, P_G: 0.25, P_S: 0.1 },
    { complexity_level: 'Medium', P_T: 0.15, P_L0: 0.2, P_G: 0.25, P_S: 0.1 },
    { complexity_level: 'High', P_T: 0.05, P_L0: 0.2, P_G: 0.25, P_S: 0.1 },
  ]);

  // Insert Bloom level weights
  await knex('bloom_level_weights').insert([
    { bloom_level: 'Remembering', weight: 0.8 },
    { bloom_level: 'Understanding', weight: 1.0 },
    { bloom_level: 'Applying', weight: 1.1 },
    { bloom_level: 'Analyzing', weight: 1.2 },
    { bloom_level: 'Evaluating', weight: 1.3 },
    { bloom_level: 'Creating', weight: 1.4 },
  ]);

  // Insert Bloom levels
  await knex('bloom_levels').insert([
    {
      level: 'Remembering',
      description: 'Recall facts and basic concepts',
      order_index: 1,
    },
    {
      level: 'Understanding',
      description: 'Explain ideas or concepts',
      order_index: 2,
    },
    {
      level: 'Applying',
      description: 'Use information in new situations',
      order_index: 3,
    },
    {
      level: 'Analyzing',
      description: 'Draw connections among ideas',
      order_index: 4,
    },
    {
      level: 'Evaluating',
      description: 'Justify a stand or decision',
      order_index: 5,
    },
    {
      level: 'Creating',
      description: 'Produce new or original work',
      order_index: 6,
    },
  ]);
};
