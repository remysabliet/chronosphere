/**
 * @param { import("knex").Knex } knex
 * @returns { Promise<void> }
 */
export const seed = async function (knex) {
  // Deletes ALL existing entries
  await knex('users').del();
  await knex('user_roles').del();

  // Insert user roles
  await knex('user_roles').insert([
    {
      role_id: '550e8400-e29b-41d4-a716-446655440001',
      role_name: 'learner',
      description:
        'Standard learning user with access to learning content and progress tracking',
      permissions: JSON.stringify([
        'view_content',
        'take_quizzes',
        'view_progress',
        'update_profile',
      ]),
    },
    {
      role_id: '550e8400-e29b-41d4-a716-446655440002',
      role_name: 'admin',
      description:
        'System administrator with full access to all features and user management',
      permissions: JSON.stringify([
        'manage_users',
        'manage_content',
        'view_analytics',
        'system_settings',
        'moderate_content',
      ]),
    },
    {
      role_id: '550e8400-e29b-41d4-a716-446655440003',
      role_name: 'moderator',
      description:
        'Content moderator with ability to review and moderate user-generated content',
      permissions: JSON.stringify([
        'moderate_content',
        'view_reports',
        'manage_questions',
        'review_validation_logs',
      ]),
    },
    {
      role_id: '550e8400-e29b-41d4-a716-446655440004',
      role_name: 'content_creator',
      description:
        'Content creator with ability to create and manage learning materials',
      permissions: JSON.stringify([
        'create_content',
        'manage_questions',
        'view_analytics',
        'edit_learning_units',
      ]),
    },
    {
      role_id: '550e8400-e29b-41d4-a716-446655440005',
      role_name: 'analyst',
      description:
        'Data analyst with access to analytics and reporting features',
      permissions: JSON.stringify([
        'view_analytics',
        'export_data',
        'generate_reports',
        'view_user_progress',
      ]),
    },
  ]);

  // Insert sample users
  await knex('users').insert([
    {
      user_id: '660e8400-e29b-41d4-a716-446655440001',
      name: 'John Doe',
      email: 'john.doe@example.com',
      age: 28,
      profession: 'Software Developer',
      education: 'Computer Science',
      role_id: '550e8400-e29b-41d4-a716-446655440001',
      consent_for_personalization: true,
      personalization_consent_timestamp: knex.fn.now(),
      created_at: knex.fn.now(),
      language_preference: 'en',
      account_status: 'active',
    },
    {
      user_id: '660e8400-e29b-41d4-a716-446655440002',
      name: 'Jane Smith',
      email: 'jane.smith@example.com',
      age: 32,
      profession: 'Data Scientist',
      education: 'Statistics',
      role_id: '550e8400-e29b-41d4-a716-446655440002',
      consent_for_personalization: true,
      personalization_consent_timestamp: knex.fn.now(),
      created_at: knex.fn.now(),
      language_preference: 'en',
      account_status: 'active',
    },
    {
      user_id: '660e8400-e29b-41d4-a716-446655440003',
      name: 'Mike Johnson',
      email: 'mike.johnson@example.com',
      age: 25,
      profession: 'Student',
      education: 'Engineering',
      role_id: '550e8400-e29b-41d4-a716-446655440001',
      consent_for_personalization: false,
      created_at: knex.fn.now(),
      language_preference: 'en',
      account_status: 'active',
    },
  ]);
};
