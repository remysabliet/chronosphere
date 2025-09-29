/**
 * @param { import("knex").Knex } knex
 * @returns { Promise<void> } 
 */
export const seed = async function (knex) {
  // Deletes ALL existing entries
  await knex('question_feedback_log').del();
  await knex('question_validation_log').del();
  await knex('review_queue_archive').del();
  await knex('review_queue').del();
  await knex('concept_progress_tracker').del();
  await knex('learning_path_log').del();
  await knex('mastery_log').del();
  await knex('user_responses').del();
  await knex('quiz_sessions').del();

  // Insert sample quiz sessions
  await knex('quiz_sessions').insert([
    {
      session_id: '990e8400-e29b-41d4-a716-446655440001',
      user_id: '660e8400-e29b-41d4-a716-446655440001',
      thema: 'Machine Learning',
      topic: 'Supervised Learning',
      session_type: 'learning',
      start_time: knex.fn.now(),
      end_time: knex.raw('NOW() + INTERVAL \'30 minutes\''),
      total_questions: 5,
      correct_answers: 4,
      total_time_seconds: 1800,
      session_status: 'completed',
      difficulty_progression: JSON.stringify([0.5, 0.7, 0.8, 1.0, 1.2]),
      bloom_level_distribution: JSON.stringify({ 'Remembering': 2, 'Understanding': 2, 'Applying': 1 }),
      session_goals: JSON.stringify(['Master linear regression basics', 'Practice calculation problems']),
      completion_rate: 0.8,
      average_response_time: 45.5,
      confidence_trend: JSON.stringify([0.6, 0.7, 0.8, 0.9, 0.85]),
      mastery_gains: JSON.stringify({ 'Linear Regression': 0.15, 'Decision Trees': 0.1 })
    }
  ]);

  // Insert sample user responses
  await knex('user_responses').insert([
    {
      id: 'aa0e8400-e29b-41d4-a716-446655440001',
      session_id: '990e8400-e29b-41d4-a716-446655440001',
      user_id: '660e8400-e29b-41d4-a716-446655440001',
      question_id: '880e8400-e29b-41d4-a716-446655440001',
      concept_id: '770e8400-e29b-41d4-a716-446655440001',
      bloom_level: 'Remembering',
      selected_option: 'To predict continuous values',
      is_correct: true,
      confidence_level: 'High',
      response_time: 30,
      decision_type: 'Advance',
      timestamp: knex.fn.now(),
      attempt_quality: 'Good',
      question_sequence_order: 1
    },
    {
      id: 'aa0e8400-e29b-41d4-a716-446655440002',
      session_id: '990e8400-e29b-41d4-a716-446655440001',
      user_id: '660e8400-e29b-41d4-a716-446655440001',
      question_id: '880e8400-e29b-41d4-a716-446655440002',
      concept_id: '770e8400-e29b-41d4-a716-446655440001',
      bloom_level: 'Applying',
      selected_option: '13',
      is_correct: true,
      confidence_level: 'Medium',
      response_time: 60,
      decision_type: 'Advance',
      timestamp: knex.fn.now(),
      attempt_quality: 'Good',
      question_sequence_order: 2
    }
  ]);

  // Insert sample mastery log
  await knex('mastery_log').insert([
    {
      user_id: '660e8400-e29b-41d4-a716-446655440001',
      concept_id: '770e8400-e29b-41d4-a716-446655440001',
      bloom_level: 'Remembering',
      thema: 'Machine Learning',
      topic: 'Supervised Learning',
      mastery_date: knex.fn.now(),
      P_Ln_at_mastery: 0.85,
      theta_at_mastery: 1.2,
      bloom_levels_assessed: ['Remembering', 'Understanding'],
      slip_count_recent: 0,
      decision_type: 'Advance',
      feedback_text: 'Excellent understanding of linear regression fundamentals',
      last_reinforced: knex.fn.now(),
      decay_threshold_days: 14,
      decay_status: 'Active',
      mastery_status: 'Mastered',
      review_count: 1,
      last_review_outcome: 'Passed',
      slip_rate: 0.0,
      version: '1.0',
      author: 'AI-generated'
    }
  ]);

  // Insert sample concept progress tracker
  await knex('concept_progress_tracker').insert([
    {
      user_id: '660e8400-e29b-41d4-a716-446655440001',
      concept_id: '770e8400-e29b-41d4-a716-446655440001',
      bloom_level: 'Remembering',
      first_attempt: knex.fn.now(),
      last_attempt: knex.fn.now(),
      attempt_count: 3,
      correct_count: 3,
      slip_count: 0,
      mastery_status: 'Mastered'
    }
  ]);
};
