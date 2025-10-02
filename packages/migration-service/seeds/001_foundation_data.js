/**
 * @param { import("knex").Knex } knex
 * @returns { Promise<void> }
 */
export const seed = async function (knex) {
  // Deletes ALL existing entries
  await knex('bkt_parameter_defaults').del();
  await knex('irt_bloom_defaults').del();
  await knex('irt_guessing_defaults').del();
  await knex('bloom_level_weights').del();
  await knex('bloom_levels').del();

  // Insert BKT parameter defaults
  await knex('bkt_parameter_defaults').insert([
    { complexity_level: 'Low', P_T: 0.25, P_L0: 0.2, P_G: 0.25, P_S: 0.1 },
    { complexity_level: 'Medium', P_T: 0.15, P_L0: 0.2, P_G: 0.25, P_S: 0.1 },
    { complexity_level: 'High', P_T: 0.05, P_L0: 0.2, P_G: 0.25, P_S: 0.1 },
  ]);

  // Insert IRT Bloom defaults
  await knex('irt_bloom_defaults').insert([
    {
      bloom_level: 'Remembering',
      difficulty_b_min: -2.0,
      difficulty_b_max: -0.5,
      discrimination_a_min: 0.5,
      discrimination_a_max: 0.7,
    },
    {
      bloom_level: 'Understanding',
      difficulty_b_min: -1.0,
      difficulty_b_max: 0.5,
      discrimination_a_min: 0.6,
      discrimination_a_max: 0.8,
    },
    {
      bloom_level: 'Applying',
      difficulty_b_min: 0.0,
      difficulty_b_max: 1.5,
      discrimination_a_min: 0.8,
      discrimination_a_max: 1.0,
    },
    {
      bloom_level: 'Analyzing',
      difficulty_b_min: 0.5,
      difficulty_b_max: 2.0,
      discrimination_a_min: 1.0,
      discrimination_a_max: 1.2,
    },
    {
      bloom_level: 'Evaluating',
      difficulty_b_min: 1.0,
      difficulty_b_max: 2.5,
      discrimination_a_min: 1.2,
      discrimination_a_max: 1.4,
    },
    {
      bloom_level: 'Creating',
      difficulty_b_min: 1.5,
      difficulty_b_max: 3.0,
      discrimination_a_min: 1.3,
      discrimination_a_max: 1.5,
    },
  ]);

  // Insert IRT guessing defaults
  await knex('irt_guessing_defaults').insert([
    { question_type: '2-option MCQ', guessing_c: 0.5 },
    { question_type: '3-option MCQ', guessing_c: 0.33 },
    { question_type: '4-option MCQ', guessing_c: 0.25 },
    { question_type: '5-option MCQ', guessing_c: 0.2 },
    { question_type: 'True/False', guessing_c: 0.5 },
    { question_type: 'Fill-in-the-Blank', guessing_c: 0.1 },
    { question_type: 'Short Answer', guessing_c: 0.05 },
    { question_type: 'Matching', guessing_c: 0.15 },
    { question_type: 'Open-ended', guessing_c: 0.01 },
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
