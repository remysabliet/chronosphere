# Memosphere Database Schema

## User Management Tables

CREATE TABLE user_roles (
role_id UUID PRIMARY KEY,
role_name TEXT NOT NULL UNIQUE,
description TEXT,
permissions JSON, -- Array of permission strings
created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
is_active BOOLEAN DEFAULT TRUE
);

-- Indexes for user_roles
CREATE INDEX idx_user_roles_name ON user_roles(role_name);
CREATE INDEX idx_user_roles_active ON user_roles(is_active);

-- Constraints for user_roles
ALTER TABLE user_roles ADD CONSTRAINT chk_role_name
CHECK (role_name IN ('learner', 'admin', 'moderator', 'content_creator', 'analyst'));

-- Insert default user roles
INSERT INTO user_roles (role_id, role_name, description, permissions) VALUES
('learner-role-uuid', 'learner', 'Standard learning user with access to learning content and progress tracking',
'["view_content", "take_quizzes", "view_progress", "update_profile"]'),
('admin-role-uuid', 'admin', 'System administrator with full access to all features and user management',
'["manage_users", "manage_content", "view_analytics", "system_settings", "moderate_content"]'),
('moderator-role-uuid', 'moderator', 'Content moderator with ability to review and moderate user-generated content',
'["moderate_content", "view_reports", "manage_questions", "review_validation_logs"]'),
('content-creator-role-uuid', 'content_creator', 'Content creator with ability to create and manage learning materials',
'["create_content", "manage_questions", "view_analytics", "edit_learning_units"]'),
('analyst-role-uuid', 'analyst', 'Data analyst with access to analytics and reporting features',
'["view_analytics", "export_data", "generate_reports", "view_user_progress"]');

CREATE TABLE users (
user_id UUID PRIMARY KEY,
name TEXT,
email TEXT,
age INT,
profession TEXT,
education TEXT,
role_id UUID,
consent_for_personalization BOOLEAN DEFAULT FALSE,
personalization_consent_timestamp DATETIME,
created_at DATETIME NOT NULL,
last_login_at DATETIME,
language_preference TEXT DEFAULT 'en',
account_status TEXT DEFAULT 'active'
);

-- Indexes for users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_last_login ON users(last_login_at);
CREATE INDEX idx_users_role ON users(role_id);

-- Constraints for users
ALTER TABLE users ADD CONSTRAINT fk_users_role
FOREIGN KEY (role_id) REFERENCES user_roles(role_id) ON DELETE SET NULL;

## Learning Content Tables

CREATE TABLE user_thema_exposure (
user_id UUID NOT NULL,
thema TEXT NOT NULL,
exposure_level TEXT NOT NULL,
source TEXT,
timestamp DATETIME NOT NULL,
notes TEXT,
PRIMARY KEY (user_id, thema)
);

-- Indexes for user_thema_exposure
CREATE INDEX idx_user_thema_exposure_user_thema ON user_thema_exposure(user_id, thema);
CREATE INDEX idx_user_thema_exposure_timestamp ON user_thema_exposure(timestamp);

-- Constraints for user_thema_exposure
ALTER TABLE user_thema_exposure ADD CONSTRAINT chk_exposure_level
CHECK (exposure_level IN ('Unseen', 'Recognized', 'Practiced', 'Mastered'));

ALTER TABLE user_thema_exposure ADD CONSTRAINT fk_user_thema_exposure_user
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

CREATE TABLE learning_units (
id UUID PRIMARY KEY,
thema TEXT NOT NULL,
topic TEXT,
concept_name TEXT NOT NULL,
learning_goal TEXT,
bloom_levels_supported TEXT[],
estimated_time_minutes INT,
bloom_coverage_score INT,
complexity_level TEXT REFERENCES bkt_parameter_defaults(complexity_level),
created_by TEXT,
created_at DATETIME NOT NULL,
author TEXT,
version TEXT,
embedding VECTOR(1024) -- mistral-embed vector; NULL until embedded (see question-diversity-and-dedup.md)
);

-- Indexes for learning_units
CREATE INDEX idx_learning_units_thema_topic ON learning_units(thema, topic);
CREATE INDEX idx_learning_units_concept ON learning_units(concept_name);
CREATE INDEX idx_learning_units_embedding_hnsw ON learning_units USING hnsw (embedding vector_cosine_ops);

-- Constraints for learning_units
ALTER TABLE learning_units ADD CONSTRAINT fk_learning_units_complexity
FOREIGN KEY (complexity_level) REFERENCES bkt_parameter_defaults(complexity_level);

CREATE TABLE questions (
id UUID PRIMARY KEY,
concept_id UUID NOT NULL,
bloom_level TEXT NOT NULL,
difficulty_tier TEXT DEFAULT 'medium',
question_type TEXT,
question_text TEXT NOT NULL,
options JSONB,
correct_answers JSONB,
explanation TEXT,
estimated_time TEXT,
tags TEXT[],
language TEXT,
source TEXT,
version TEXT,
created_by TEXT,
owner_user_id UUID, -- NULL = public shared pool; non-NULL = private to that user (document-sourced)
created_at DATETIME NOT NULL,
embedding VECTOR(1024), -- mistral-embed vector; NULL until embedded (see question-diversity-and-dedup.md)
question_text_norm_hash TEXT GENERATED ALWAYS AS (
md5(lower(regexp_replace(question_text, '\s+', ' ', 'g')))
) STORED -- cheap write-time exact-duplicate guard for the public pool
);

-- Indexes for questions (partial per pool: public scans never touch private rows)
CREATE INDEX idx_questions_public_pool ON questions(concept_id, bloom_level, difficulty_tier)
WHERE owner_user_id IS NULL;
CREATE INDEX idx_questions_private_pool ON questions(owner_user_id, concept_id, bloom_level, difficulty_tier)
WHERE owner_user_id IS NOT NULL;
CREATE INDEX idx_questions_embedding_hnsw ON questions USING hnsw (embedding vector_cosine_ops);
-- Public-pool exact-duplicate guard: same concept/bloom/difficulty/normalized text
CREATE UNIQUE INDEX idx_questions_concept_text_dedup
ON questions (concept_id, bloom_level, difficulty_tier, question_text_norm_hash)
WHERE owner_user_id IS NULL;

-- Constraints for questions
ALTER TABLE questions ADD CONSTRAINT chk_questions_difficulty_tier
CHECK (difficulty_tier IN ('easy', 'medium', 'hard'));

ALTER TABLE questions ADD CONSTRAINT fk_questions_concept
FOREIGN KEY (concept_id) REFERENCES learning_units(id) ON DELETE CASCADE;

ALTER TABLE questions ADD CONSTRAINT fk_questions_owner
FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE;

CREATE TABLE bloom_levels (
level TEXT PRIMARY KEY,
description TEXT,
order_index INT
);

## Quiz Session Tables

-- Transactional outbox: events that must never be lost are inserted here in
-- the same transaction as the domain write; a relay publishes unpublished
-- rows (in id order) to the matching Redis stream, then stamps published_at.
CREATE TABLE outbox (
id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
topic TEXT NOT NULL, -- e.g. 'events:response.recorded', 'jobs:generate-questions'
payload JSONB NOT NULL,
created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
published_at DATETIME -- NULL until the relay has published it
);

CREATE INDEX idx_outbox_unpublished ON outbox(id) WHERE published_at IS NULL;

-- Claim check for one jobs:generate-questions stream message: the worker
-- inserts message_id here (ON CONFLICT DO NOTHING) before incrementing
-- quizzes.generation_questions_ready, so at-least-once redelivery can't
-- double-count a batch that already completed.
CREATE TABLE generation_job_completions (
message_id TEXT PRIMARY KEY,
completed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- A quiz is a user-owned configuration (thema + wizard choices), not the
-- questions: questions live in the shared/private pools, sessions are runs
-- of a quiz. visibility gates sharing; private quizzes are owner-only.
-- Deletion is a SOFT delete (deleted_at): session history must outlive the
-- quiz config (title, topics, per-question review stay resolvable), so the
-- row is tombstoned, hidden from listings/detail/session-start, and only a
-- future retention job may hard-purge it.
CREATE TABLE quizzes (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
owner_user_id UUID NOT NULL,
thema TEXT NOT NULL,
title TEXT NOT NULL,
question_types TEXT[] NOT NULL, -- allowed types chosen in the wizard
question_count INT, -- desired size; NULL when time-based
time_limit_minutes INT, -- NULL when count-based
visibility TEXT NOT NULL DEFAULT 'private', -- 'private', 'shared', 'public'
generation_questions_ready INT NOT NULL DEFAULT 0, -- incremented by the worker as jobs:generate-questions batches complete
created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
deleted_at TIMESTAMPTZ -- soft-delete tombstone; NULL = live
);

-- Indexes for quizzes
-- Partial: listings only ever read live rows, so tombstones never bloat the
-- hot per-owner index.
CREATE INDEX idx_quizzes_owner_recent ON quizzes(owner_user_id, updated_at)
WHERE deleted_at IS NULL;
CREATE INDEX idx_quizzes_owner_thema ON quizzes(owner_user_id, thema);

-- Constraints for quizzes
ALTER TABLE quizzes ADD CONSTRAINT chk_quizzes_visibility
CHECK (visibility IN ('private', 'shared', 'public'));

ALTER TABLE quizzes ADD CONSTRAINT chk_quizzes_question_types
CHECK (cardinality(question_types) >= 1
AND question_types <@ ARRAY['MCQ', 'MCQMultiSelect', 'TrueFalse', 'FillInBlank']::text[]);

ALTER TABLE quizzes ADD CONSTRAINT chk_quizzes_has_size
CHECK (question_count IS NOT NULL OR time_limit_minutes IS NOT NULL);

ALTER TABLE quizzes ADD CONSTRAINT fk_quizzes_owner
FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE;

CREATE TABLE quiz_sessions (
session_id UUID PRIMARY KEY,
user_id UUID NOT NULL,
quiz_id UUID, -- the quiz this session is a run of; NULL for non-quiz session types
question_ids UUID[] NOT NULL DEFAULT '{}', -- frozen, ordered question set chosen at session start
thema TEXT,
topic TEXT,
session_type TEXT DEFAULT 'learning', -- 'learning', 'review', 'assessment'
start_time DATETIME NOT NULL,
end_time DATETIME,
total_questions INT DEFAULT 0,
correct_answers INT DEFAULT 0,
total_time_seconds INT,
session_status TEXT DEFAULT 'active', -- 'active', 'completed', 'abandoned'
difficulty_progression JSON, -- Track difficulty changes during session
bloom_level_distribution JSON, -- Distribution of Bloom levels in session
session_goals JSON, -- Learning objectives for this session
completion_rate FLOAT,
average_response_time FLOAT,
confidence_trend JSON, -- Track confidence changes over time
mastery_gains JSON, -- Track P(Ln) improvements during session
created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for quiz_sessions
-- (user_id, start_time DESC) serves the History page's
-- "my sessions, newest first" directly; it also covers plain user_id lookups
-- (leftmost prefix), so no single-column user_id index.
CREATE INDEX idx_quiz_sessions_user_recent ON quiz_sessions(user_id, start_time DESC);
CREATE INDEX idx_quiz_sessions_start_time ON quiz_sessions(start_time);
CREATE INDEX idx_quiz_sessions_status ON quiz_sessions(session_status);
CREATE INDEX idx_quiz_sessions_type ON quiz_sessions(session_type);

-- Constraints for quiz_sessions
ALTER TABLE quiz_sessions ADD CONSTRAINT chk_session_type
CHECK (session_type IN ('learning', 'review', 'assessment'));

ALTER TABLE quiz_sessions ADD CONSTRAINT chk_session_status
CHECK (session_status IN ('active', 'completed', 'abandoned'));

ALTER TABLE quiz_sessions ADD CONSTRAINT fk_quiz_sessions_user
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

CREATE INDEX idx_quiz_sessions_quiz_user ON quiz_sessions(quiz_id, user_id);

-- SET NULL, never CASCADE: a learner's session history outlives the quiz
-- config. Quiz deletion is a soft delete anyway (quizzes.deleted_at); this
-- FK only fires if a retention job hard-purges old tombstones.
ALTER TABLE quiz_sessions ADD CONSTRAINT fk_quiz_sessions_quiz
FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE SET NULL;

CREATE TABLE user_responses (
id UUID PRIMARY KEY,
session_id UUID,
user_id UUID NOT NULL,
question_id UUID NOT NULL,
concept_id UUID NOT NULL,
bloom_level TEXT NOT NULL,
selected_option TEXT,
is_correct BOOLEAN,
confidence_level TEXT,
response_time INT,
decision_type TEXT,
timestamp DATETIME NOT NULL,
attempt_quality TEXT,
question_sequence_order INT -- Order within the session
);

-- Indexes for user_responses
CREATE INDEX idx_user_responses_user_concept_bloom ON user_responses(user_id, concept_id, bloom_level);
CREATE INDEX idx_user_responses_question ON user_responses(question_id);
CREATE INDEX idx_user_responses_timestamp ON user_responses(timestamp);
CREATE INDEX idx_user_responses_correct ON user_responses(is_correct);
CREATE INDEX idx_user_responses_decision_type ON user_responses(decision_type);
CREATE INDEX idx_user_responses_user_correct_timestamp ON user_responses(user_id, is_correct, timestamp);
CREATE INDEX idx_user_responses_session_id ON user_responses(session_id);

-- Constraints for user_responses
ALTER TABLE user_responses ADD CONSTRAINT chk_decision_type
CHECK (decision_type IN ('Review', 'Practice', 'Advance', 'Remediate'));

ALTER TABLE user_responses ADD CONSTRAINT chk_confidence_level
CHECK (confidence_level IN ('Low', 'Medium', 'High'));

ALTER TABLE user_responses ADD CONSTRAINT fk_user_responses_session
FOREIGN KEY (session_id) REFERENCES quiz_sessions(session_id) ON DELETE SET NULL;

ALTER TABLE user_responses ADD CONSTRAINT fk_user_responses_user
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE user_responses ADD CONSTRAINT fk_user_responses_question
FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE;

ALTER TABLE user_responses ADD CONSTRAINT fk_user_responses_concept
FOREIGN KEY (concept_id) REFERENCES learning_units(id) ON DELETE CASCADE;

## Mastery and Progress Tracking Tables

CREATE TABLE mastery_log (
user_id UUID NOT NULL,
concept_id UUID NOT NULL,
bloom_level TEXT NOT NULL,
thema TEXT NOT NULL,
topic TEXT,
mastery_date DATETIME NOT NULL,
P_Ln_at_mastery FLOAT NOT NULL,
bloom_levels_assessed TEXT[] NOT NULL,
slip_count_recent INT DEFAULT 0,
decision_type TEXT NOT NULL,
feedback_text TEXT,
last_reinforced DATETIME,
fsrs_state JSON, -- FSRS memory state; predicted recall is the decay signal
next_review_at DATETIME,
mastery_status TEXT DEFAULT 'In Progress',
review_count INT DEFAULT 0,
last_review_outcome TEXT,
slip_rate FLOAT DEFAULT 0.0,
version TEXT,
author TEXT DEFAULT 'AI-generated',
usage_stats JSON,
PRIMARY KEY (user_id, concept_id, bloom_level)
);

-- Indexes for mastery_log
CREATE INDEX idx_mastery_log_user_concept_bloom ON mastery_log(user_id, concept_id, bloom_level);
CREATE INDEX idx_mastery_log_next_review ON mastery_log(user_id, next_review_at);

-- Constraints for mastery_log
ALTER TABLE mastery_log ADD CONSTRAINT chk_mastery_status
CHECK (mastery_status IN ('In Progress', 'Mastered', 'Expired'));

ALTER TABLE mastery_log ADD CONSTRAINT fk_mastery_log_user
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE mastery_log ADD CONSTRAINT fk_mastery_log_concept
FOREIGN KEY (concept_id) REFERENCES learning_units(id) ON DELETE CASCADE;

CREATE TABLE learning_path_log (
user_id UUID NOT NULL,
concept_id UUID NOT NULL,
bloom_level TEXT NOT NULL,
decision_type TEXT,
timestamp DATETIME NOT NULL,
triggered_by TEXT
);

-- Constraints for learning_path_log
ALTER TABLE learning_path_log ADD CONSTRAINT fk_learning_path_log_user
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE learning_path_log ADD CONSTRAINT fk_learning_path_log_concept
FOREIGN KEY (concept_id) REFERENCES learning_units(id) ON DELETE CASCADE;

CREATE TABLE concept_progress_tracker (
user_id UUID NOT NULL,
concept_id UUID NOT NULL,
bloom_level TEXT NOT NULL,
p_ln FLOAT, -- current BKT mastery probability for this pair
first_attempt DATETIME,
last_attempt DATETIME,
attempt_count INT,
correct_count INT,
slip_count INT,
mastery_status TEXT,
PRIMARY KEY (user_id, concept_id, bloom_level)
);

-- Indexes for concept_progress_tracker
CREATE INDEX idx_concept_progress_tracker_user_concept_bloom ON concept_progress_tracker(user_id, concept_id, bloom_level);

-- Constraints for concept_progress_tracker
ALTER TABLE concept_progress_tracker ADD CONSTRAINT chk_mastery_status_tracker
CHECK (mastery_status IN ('In Progress', 'Mastered', 'Expired'));

ALTER TABLE concept_progress_tracker ADD CONSTRAINT fk_concept_progress_tracker_user
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE concept_progress_tracker ADD CONSTRAINT fk_concept_progress_tracker_concept
FOREIGN KEY (concept_id) REFERENCES learning_units(id) ON DELETE CASCADE;

## Review and Queue Tables

CREATE TABLE review_queue (
user_id UUID NOT NULL,
concept_id UUID NOT NULL,
bloom_level TEXT NOT NULL,
question_id UUID,
outcome TEXT,
response_time INT,
timestamp DATETIME NOT NULL,
PRIMARY KEY (user_id, concept_id, bloom_level)
);

-- Indexes for review_queue
CREATE INDEX idx_review_queue_user_concept_bloom ON review_queue(user_id, concept_id, bloom_level);
CREATE INDEX idx_review_queue_timestamp ON review_queue(timestamp);

-- Constraints for review_queue
ALTER TABLE review_queue ADD CONSTRAINT fk_review_queue_user
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE review_queue ADD CONSTRAINT fk_review_queue_concept
FOREIGN KEY (concept_id) REFERENCES learning_units(id) ON DELETE CASCADE;

ALTER TABLE review_queue ADD CONSTRAINT fk_review_queue_question
FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE SET NULL;

CREATE TABLE review_queue_archive (
id UUID PRIMARY KEY,
user_id UUID NOT NULL,
concept_id UUID NOT NULL,
bloom_level TEXT NOT NULL,
question_id UUID NOT NULL,
outcome TEXT NOT NULL,
response_time INT,
timestamp DATETIME NOT NULL,
review_trigger TEXT, -- what queued this review (e.g., 'low predicted recall')
source TEXT,
notes TEXT,
version TEXT,
archived_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for review_queue_archive
CREATE INDEX idx_review_archive_user_concept_bloom ON review_queue_archive(user_id, concept_id, bloom_level);
CREATE INDEX idx_review_archive_timestamp ON review_queue_archive(timestamp);

-- Constraints for review_queue_archive
ALTER TABLE review_queue_archive ADD CONSTRAINT fk_review_queue_archive_user
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE review_queue_archive ADD CONSTRAINT fk_review_queue_archive_concept
FOREIGN KEY (concept_id) REFERENCES learning_units(id) ON DELETE CASCADE;

ALTER TABLE review_queue_archive ADD CONSTRAINT fk_review_queue_archive_question
FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE;

CREATE TABLE question_validation_log (
id UUID PRIMARY KEY,
question_id UUID,
validation_status TEXT NOT NULL, -- "Passed", "Failed"
failed_checks TEXT[], -- e.g., ["Missing explanation", "Invalid difficulty tier"]
timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
notes TEXT,
validation_score FLOAT, -- Overall validation score (0.0 to 1.0)
validator_version TEXT -- Version of validation logic used
);

-- Indexes for question_validation_log
CREATE INDEX idx_question_validation_log_question_id ON question_validation_log(question_id);
CREATE INDEX idx_question_validation_log_status ON question_validation_log(validation_status);
CREATE INDEX idx_question_validation_log_timestamp ON question_validation_log(timestamp);

-- Constraints for question_validation_log
ALTER TABLE question_validation_log ADD CONSTRAINT chk_validation_status
CHECK (validation_status IN ('Passed', 'Failed', 'Warning'));

ALTER TABLE question_validation_log ADD CONSTRAINT fk_question_validation_log_question
FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE;

CREATE TABLE question_feedback_log (
id UUID PRIMARY KEY,
user_id UUID NOT NULL,
question_id UUID NOT NULL,
response_id UUID NOT NULL,
rating INT, -- Optional: 1 to 5 stars
flag_reason TEXT, -- Optional: "Confusing", "Incorrect", etc.
notes TEXT, -- Optional learner comment
timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for question_feedback_log
CREATE INDEX idx_question_feedback_log_user ON question_feedback_log(user_id);
CREATE INDEX idx_question_feedback_log_question ON question_feedback_log(question_id);
CREATE INDEX idx_question_feedback_log_response ON question_feedback_log(response_id);
CREATE INDEX idx_question_feedback_log_rating ON question_feedback_log(rating);
CREATE INDEX idx_question_feedback_log_flag ON question_feedback_log(flag_reason);

-- Constraints for question_feedback_log
ALTER TABLE question_feedback_log ADD CONSTRAINT chk_rating
CHECK (rating BETWEEN 1 AND 5);

ALTER TABLE question_feedback_log ADD CONSTRAINT chk_flag_reason
CHECK (flag_reason IN ('Confusing', 'Incorrect', 'Too Easy', 'Too Hard', 'Poorly Worded', 'Technical Error'));

ALTER TABLE question_feedback_log ADD CONSTRAINT fk_feedback_user
FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;

ALTER TABLE question_feedback_log ADD CONSTRAINT fk_feedback_question
FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE;

ALTER TABLE question_feedback_log ADD CONSTRAINT fk_feedback_response
FOREIGN KEY (response_id) REFERENCES user_responses(id) ON DELETE CASCADE;

## Configuration and Default Tables

CREATE TABLE bkt_parameter_defaults (
complexity_level TEXT PRIMARY KEY,
P_T FLOAT NOT NULL,
P_L0 FLOAT DEFAULT 0.2,
P_G FLOAT DEFAULT 0.25,
P_S FLOAT DEFAULT 0.1
);

INSERT INTO bkt_parameter_defaults (complexity_level, P_T, P_L0, P_G, P_S) VALUES
('Low', 0.25, 0.2, 0.25, 0.1),
('Medium', 0.15, 0.2, 0.25, 0.1),
('High', 0.05, 0.2, 0.25, 0.1);

CREATE TABLE bloom_level_weights (
bloom_level TEXT PRIMARY KEY, -- e.g., "Remembering", "Applying"
weight FLOAT NOT NULL -- Scaling factor for BKT update
);

INSERT INTO bloom_level_weights (bloom_level, weight) VALUES
('Remembering', 0.8),
('Understanding', 1.0),
('Applying', 1.1),
('Analyzing', 1.2),
('Evaluating', 1.3),
('Creating', 1.4);
