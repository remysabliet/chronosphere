# 🧠 Adaptive Learning Workflow (Memosphere Engine)

# 🔹 Step 1: User Account Creation
- Collect basic profile information (optional):
  - Age or age range
  - Profession or role
  - Education level
- Assign user role (default: 'learner'):
  - **learner**: Standard learning user
  - **admin**: System administrator
  - **moderator**: Content moderator
  - **content_creator**: Learning material creator
  - **analyst**: Data analyst
- Store in: `user_profile` and `user_roles`

# 🔹 Step 2: Role-Based Access Control
**Purpose**: Ensure users have appropriate permissions for their role

## 🔹 Step 2A: Permission Validation
- Check user role permissions before allowing actions:
  - **Content Access**: Verify user can view/access learning materials
  - **Quiz Participation**: Ensure user can take quizzes
  - **Analytics Access**: Validate permissions for viewing analytics
  - **Content Management**: Check permissions for creating/editing content
  - **User Management**: Verify admin permissions for user management

## 🔹 Step 2B: Role-Specific Features
- **Learner**: Access to learning content, progress tracking, quizzes
- **Admin**: Full system access, user management, analytics, settings
- **Moderator**: Content moderation, question review, validation logs
- **Content Creator**: Create/edit learning materials, manage questions
- **Analyst**: View analytics, generate reports, export data

# 🔹 Step 3: Spaced Repetition Review Workflow

## 🔹 Step A: Scheduled Decay Check (Daily or on Login)
- Scan `mastery_log` for entries where:
  - `decay_status = 'Active'`
  - `mastery_date + decay_threshold_days ≤ NOW()`
- For each match:
  - Call `apply_decay()` to compute decayed P(Ln)
  - Update `mastery_log` with new P(Ln)
  - Set `decay_status = 'Pending review'`
  - Optionally insert into `review_queue` or flag for dynamic review

## 🔹 Step B: Pre-Session Planning
- Scan `mastery_log` for:
  - `decay_status IN ('Expired', 'Pending review')`
  - `last_reinforced + decay_threshold_days ≤ NOW()`
- Populate `session_review_queue` with concept–Bloom pairs
- Present "Memory Refresh" module before new learning begins

## 🔹 Step C: Review Question Selection
For each concept–Bloom pair in review queue:
- Query `user_responses` for:
  - `user_id = X`
  - `concept_id = Y`
  - `bloom_level = Z`
  - `is_correct = FALSE`
  - Optional: `decision_type IN ('Advance', 'Reinforce')`
- Rank candidates by:
  - Most recent incorrect attempts
  - Highest slip count
  - Longest response time
- **Fallback**: If no incorrect responses exist, select a fresh question from `questions` using:
  - Matching `concept_id` and `bloom_level`
  - Moderate `difficulty_b ≈ θ`
  - High `discrimination_a`
  - Not recently used

## 🔹 Step D: Review Execution
- Serve selected question to learner
- After response:
  - Insert new entry into `user_responses` with:
    - `decision_type = 'Review'`
    - `is_correct`, `response_time`, `confidence_level`, etc.
  - Move review task to `review_queue_archive`
  - Delete from `review_queue`

## 🔹 Step E: Update mastery_log
For the reviewed concept–Bloom pair:
- Update reinforcement and decay status:
  - `last_reinforced = NOW()`
  - If `is_correct = TRUE`:
    - `decay_status = 'Active'`
  - If `is_correct = FALSE`:
    - ✅ Call `apply_decay()` again to penalize P(Ln)
    - `decay_status = 'Expired'`
    - Optionally downgrade mastery or requeue for remediation
- Update review stats:
  - Increment `review_count`
  - Set `last_review_outcome = 'Correct'` or `'Incorrect'`
  - Recalculate `slip_rate` based on recent review responses

# 🔹 Step 4: Quiz Session Initialization
- User provides:
  - Keywords or thema description
  - Desired Bloom level range
  - Optional: difficulty preference, time availability
- Create new quiz session:
  - Generate unique `session_id`
  - Set `session_type` (learning, review, assessment)
  - Record `start_time`
  - Initialize session tracking fields
- Store in: `quiz_metadata` and `quiz_sessions`

# 🔹 Step 5: Thema Extraction & Exposure Check (Prompt 1)

## 🎯 Purpose
Extract a standardized Thema and Topic from the user's quiz initialization input, then check whether the user has prior exposure to that Thema. This helps seed initial BKT priors and personalize the learning path.

## 🧠 Logic Flow

### Extract Thema and Topic
- Use AI to parse the user's input (keywords, description, or goal)
- Normalize the output:
  - Canonical naming (title case, no punctuation, singular form)
  - Map synonyms to a single Thema (e.g., "Photosynthesis" ← "The process of photosynthesis")

### Check Exposure
- Query `user_thema_exposure` for (user_id, thema)
- If found → retrieve exposure_level (e.g., "Unseen", "Recognized", "Practiced", "Mastered")
- If not found → ask the user:
- Store the response in `user_thema_exposure`

### Use Exposure Level to Seed BKT
Set initial P(L0) based on exposure:
- "Unseen" → 0.2
- "Recognized" → 0.4
- "Practiced" → 0.6
- "Mastered" → 0.8

# 🔹 Step 6: Concept–Bloom Mapping (prompt2)

## 🧠 Logic Flow
**Input**: Thema and Topic from Step 5

**Example**:
```json
{
  "thema": "Photosynthesis",
  "topic": "Light reactions"
}
```

### Prompt 1 Execution
- AI generates a list of atomic concepts under the Thema
- For each concept, assign feasible Bloom levels (based on cognitive task type, not difficulty)
- Store in `concept_map`
- Each entry links the Thema → Concept → Bloom level
- This becomes the scope for adaptive question generation

# 🔹 Step 7: BKT Initialization

**Prompt 3**: Generate BKT parameters per concept:
- P(L0), P(T), P(G), P(S)
- Based on: `user_profile` + `user_thema_exposure`
- Generate a complexity level per concept
- Retrieve all default BKT parameters from table `bkt_parameter_defaults` based on the complexity level retrieved from prompt2.

### In the code, apply following logic:
1. Does the user have a profile? (age, education, profession)
2. Has the user been exposed to the Thema before?
3. Provide BKT default parameters based on question above (look section bkt-initialization)

*See `python-functions.md` for the `initialize_bkt()` function implementation.*

# 🔹 Step 8: Question Generation & Validation

**Prompt 3**: Generate questions using:
- Concept–Bloom pairs
- IRT metadata: b (difficulty), a (discrimination), c (guessing)
- Current mastery model: P(Ln) from BKT, θ from IRT

## 🔹 Step 7A: Question Validation
**Purpose**: Ensure question quality before serving to learners

### Validation Checklist
For each generated question, validate:

#### ✅ Content Validation
- **Question stem**: Non-empty and grammatically valid
- **Correct answer**: Present in options and logically correct
- **Options**: Unique, plausible, and well-distributed
- **Explanation**: Present and pedagogically sound

#### ✅ Alignment Validation
- **Bloom level**: Matches cognitive demand of question
- **Difficulty range**: Within expected range for Bloom level
- **Discrimination**: Positive and reasonable (> 0)
- **Guessing rate**: Matches question type expectations

#### ✅ Technical Validation
- **Language**: Supported and matches user preference
- **Question type**: Valid and supported
- **Metadata**: Complete and consistent

### Implementation
*See `python-functions.md` for the `validate_question()` function implementation.*

### Validation Workflow
1. **Generate question** using Prompt 3
2. **Run validation** using checklist above
3. **Log validation results** in `question_validation_log`
4. **If validation passes**: Store in `question_bank`
5. **If validation fails**: Regenerate or flag for manual review

### Feedback-Based Quality Improvement
- **Use feedback logs** to improve question generation:
  - Score prompt variants based on user ratings
  - Identify weak question types from flag reasons
  - Tune Bloom-level difficulty mappings
  - Optimize generation templates based on feedback patterns

### Store Results
- **Valid questions**: Store in `question_bank`
- **Validation log**: Store in `question_validation_log` with:
  - `validation_status`: "Passed", "Failed", or "Warning"
  - `failed_checks`: Array of specific issues
  - `validation_score`: Overall quality score (0.0 to 1.0)
  - `notes`: Additional validation details

# 🔹 Step 9: Learner Interaction & Feedback Collection
- User answers question
- Log response in: `user_responses` with session tracking:
  - Link to `session_id`
  - Record `question_sequence_order`
  - Track response time, confidence, correctness
- **Collect user feedback** (optional):
  - "Was this question helpful?" (rating 1-5)
  - "Flag if confusing or incorrect" (flag_reason)
  - "Additional comments" (feedback_notes)
- Update session statistics:
  - Increment `total_questions`
  - Update `correct_answers` if correct
  - Track `difficulty_progression`
  - Update `bloom_level_distribution`
  - Record `confidence_trend`
  - Calculate `average_response_time`

# 🔹 Step 10: Model Update & Feedback Logging (use python library)
Invoke function `update_irt` and `update_bkt` in order to update:
- BKT: P(Ln) for concept
- IRT: θ for concept
- Store updated values in: `user_concept_mastery` and `user_response` table

**Log feedback data**:
- Insert feedback into `question_feedback_log` (normalized design)
- Link feedback to specific `response_id` for audit and tuning
- Use feedback for question quality improvement

*See `python-functions.md` for the `update_irt()` and `update_bkt()` function implementations.*

# 🔹 Step 11: Adaptive Decision Engine

**Purpose**: Decide what question to ask next by combining mastery signals, Bloom level history, and spaced repetition needs. This engine ensures learners are challenged appropriately, reinforced when needed, and periodically reviewed to prevent forgetting.

## 🧠 Decision Flow

### Check for Review Tasks (Spaced Repetition)
- Scan `review_queue` for entries with:
  - `status = "Pending"`
  - `scheduled_date ≤ now`
- If found:
  - Select the `concept_id` and `bloom_level` from the review entry
  - Set `decision_type = "Review"`
  - Generate a new question using Prompt 4
  - After response:
    - Update `review_queue.status = "Completed"`
    - Update `mastery_log.last_reinforced = now`
    - Set `mastery_log.decay_status = "Active"`

### Otherwise, Use Mastery Signals to Guide Selection
Based on updated BKT + IRT values for each concept–Bloom pair:

**Reinforce**
- If P(Ln) < 0.6, select a lower Bloom level and easier item (b < θ)
- Set `decision_type = "Reinforce"`

**Advance**
- If P(Ln) > 0.9 and θ > 2.5, select a higher Bloom level and harder item (b > θ)
- Set `decision_type = "Advance"`

**Remediate**
- If repeated slips or low P(Ln) persist, reselect the same concept with adjusted Bloom level or difficulty
- Set `decision_type = "Remediate"`

### Track Bloom-Level History per Concept
- Log each assessed Bloom level in `concept_progress_tracker`
- Mastery is declared per concept–Bloom pair, not per concept alone

### Skip Mastered Bloom Levels (Unless in Review Mode)
- If a concept–Bloom pair is marked as mastered in `mastery_log` and `decay_status = "Active"`, skip it
- If `decay_status = "Expired"` or "Pending review", requeue for spaced repetition

# 🔹 Step 12: Session Completion & Analytics

**Purpose**: Finalize session and generate session-level analytics

### Session Completion Process
1. **End session tracking**:
   - Set `end_time` in `quiz_sessions`
   - Calculate `total_time_seconds`
   - Update `session_status` to 'completed' or 'abandoned'
   - Calculate `completion_rate`

2. **Generate session analytics**:
   - **Performance metrics**: Accuracy rate, average response time
   - **Learning progression**: Difficulty changes, Bloom level distribution
   - **Confidence analysis**: Confidence trends over time
   - **Mastery gains**: P(Ln) improvements during session
   - **Session goals**: Achievement of learning objectives
   - **Feedback analysis**: Question ratings and flag patterns

3. **Store session results**:
   - Update `quiz_sessions` with final statistics
   - Generate session summary for user
   - Trigger analytics updates for admin/analyst roles

# 🔹 Step 12A: Feedback Analytics Dashboard (Optional - Post-MVP)

**Purpose**: Provide feedback insights for content improvement

### Feedback Analytics Views
- **Recent low-rated responses**: Spot problematic question types
- **Flag reasons by concept**: Identify confusing topics
- **Feedback by Bloom level**: Tune cognitive scaffolding
- **Feedback by prompt variant**: Optimize generation templates
- **Question quality trends**: Track improvement over time

### Analytics for Different Roles
- **Learner**: Personal feedback history and question quality insights
- **Content Creator**: Question performance metrics and improvement suggestions
- **Moderator**: Flagged questions requiring review
- **Analyst**: System-wide feedback patterns and quality trends
- **Admin**: Overall system quality metrics and improvement recommendations

# 🔹 Step 13: Feedback & Mastery Declaration

**Purpose**: Confirm and log mastery + generate feedback

Is the official declaration: "This concept is now mastered. Log it. Show feedback. Update dashboard."

### Generate personalized feedback using:
- P(Ln), θ, Bloom history
- Session performance data
- Learning progression insights

### Declare concept mastered when:
- P(Ln) > 0.9
- θ > 2.5
- ≥2 Bloom levels assessed
- No recent slips
- Store in: `mastery_log`

### Mastery should expire if not reinforced
- Use `mastery_log` to track decay and trigger review
- Extend BKT to model forgetting
- This keeps your system adaptive, honest, and pedagogically sound

---

**Mastery is tracked per concept–Bloom level pair.** Each Bloom level represents a distinct cognitive mastery state. Review and decay logic operate independently per Bloom level.