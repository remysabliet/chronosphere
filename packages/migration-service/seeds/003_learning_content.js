/**
 * @param { import("knex").Knex } knex
 * @returns { Promise<void> }
 */
export const seed = async function (knex) {
  // Deletes ALL existing entries
  await knex('questions').del();
  await knex('learning_units').del();
  await knex('user_thema_exposure').del();

  // Insert sample learning units
  await knex('learning_units').insert([
    {
      id: '770e8400-e29b-41d4-a716-446655440001',
      thema: 'Machine Learning',
      topic: 'Supervised Learning',
      concept_name: 'Linear Regression',
      learning_goal:
        'Understand the fundamentals of linear regression and its applications',
      bloom_levels_supported: ['Remembering', 'Understanding', 'Applying'],
      estimated_time_minutes: 45,
      bloom_coverage_score: 75,
      complexity_level: 'Medium',
      created_by: 'system',
      created_at: knex.fn.now(),
      author: 'AI-generated',
      version: '1.0',
    },
    {
      id: '770e8400-e29b-41d4-a716-446655440002',
      thema: 'Machine Learning',
      topic: 'Supervised Learning',
      concept_name: 'Decision Trees',
      learning_goal: 'Learn how decision trees work and when to use them',
      bloom_levels_supported: ['Understanding', 'Applying', 'Analyzing'],
      estimated_time_minutes: 60,
      bloom_coverage_score: 80,
      complexity_level: 'Medium',
      created_by: 'system',
      created_at: knex.fn.now(),
      author: 'AI-generated',
      version: '1.0',
    },
    {
      id: '770e8400-e29b-41d4-a716-446655440003',
      thema: 'Statistics',
      topic: 'Probability',
      concept_name: 'Bayes Theorem',
      learning_goal:
        'Master the application of Bayes theorem in real-world scenarios',
      bloom_levels_supported: [
        'Understanding',
        'Applying',
        'Analyzing',
        'Evaluating',
      ],
      estimated_time_minutes: 90,
      bloom_coverage_score: 85,
      complexity_level: 'High',
      created_by: 'system',
      created_at: knex.fn.now(),
      author: 'AI-generated',
      version: '1.0',
    },
  ]);

  // Insert sample questions
  await knex('questions').insert([
    {
      id: '880e8400-e29b-41d4-a716-446655440001',
      concept_id: '770e8400-e29b-41d4-a716-446655440001',
      bloom_level: 'Remembering',
      difficulty_b: 0.5,
      discrimination_a: 1.2,
      guessing_c: 0.25,
      question_type: '4-option MCQ',
      question_text: 'What is the primary goal of linear regression?',
      options: JSON.stringify([
        'To classify data into categories',
        'To predict continuous values',
        'To cluster similar data points',
        'To reduce data dimensionality',
      ]),
      correct_answer: 'To predict continuous values',
      explanation:
        'Linear regression is used to predict continuous numerical values by finding the best line through data points.',
      estimated_time: '2 minutes',
      tags: ['linear-regression', 'supervised-learning'],
      language: 'en',
      source: 'AI-generated',
      version: '1.0',
      created_by: 'system',
      created_at: knex.fn.now(),
    },
    {
      id: '880e8400-e29b-41d4-a716-446655440002',
      concept_id: '770e8400-e29b-41d4-a716-446655440001',
      bloom_level: 'Applying',
      difficulty_b: 1.2,
      discrimination_a: 1.5,
      guessing_c: 0.25,
      question_type: '4-option MCQ',
      question_text:
        'Given the equation y = 2x + 3, what would be the predicted value when x = 5?',
      options: JSON.stringify(['10', '11', '13', '15']),
      correct_answer: '13',
      explanation:
        'Substituting x = 5 into the equation: y = 2(5) + 3 = 10 + 3 = 13',
      estimated_time: '3 minutes',
      tags: ['linear-regression', 'calculation'],
      language: 'en',
      source: 'AI-generated',
      version: '1.0',
      created_by: 'system',
      created_at: knex.fn.now(),
    },
  ]);

  // Insert sample user thema exposure
  await knex('user_thema_exposure').insert([
    {
      user_id: '660e8400-e29b-41d4-a716-446655440001',
      thema: 'Machine Learning',
      exposure_level: 'Practiced',
      source: 'course',
      timestamp: knex.fn.now(),
      notes: 'Completed basic ML course',
    },
    {
      user_id: '660e8400-e29b-41d4-a716-446655440001',
      thema: 'Statistics',
      exposure_level: 'Recognized',
      source: 'self-study',
      timestamp: knex.fn.now(),
      notes: 'Started statistics fundamentals',
    },
  ]);
};
