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
- Store in: `users` and `user_roles`

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

## 🔹 Step A: Review Due Check (Daily or on Login)

- For each concept–Bloom pair in `mastery_log`, compute the FSRS predicted recall probability from `fsrs_state`
- If predicted recall < 0.90 (or `next_review_at ≤ NOW()`):
  - Insert into `review_queue`
- FSRS predicted recall is the single decay signal — no decay job, no decay-status flags

## 🔹 Step B: Pre-Session Planning

- Build the session's review list from `review_queue`, lowest predicted recall first
- Present "Memory Refresh" module before new learning begins

## 🔹 Step C: Review Question Selection

For each concept–Bloom pair in review queue:

- Query `user_responses` for:
  - `user_id = X`
  - `concept_id = Y`
  - `bloom_level = Z`
  - `is_correct = FALSE`
  - Optional: `decision_type IN ('Advance', 'Practice')`
- Rank candidates by:
  - Most recent incorrect attempts
  - Highest slip count
  - Longest response time
- **Fallback**: If no incorrect responses exist, select a fresh question from `questions` using:
  - Matching `concept_id` and `bloom_level`
  - `difficulty_tier = 'medium'`
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

- Update reinforcement state:
  - `last_reinforced = NOW()`
  - Update `fsrs_state` and `next_review_at` with the review outcome (correct → longer interval, incorrect → short interval)
  - If `is_correct = FALSE`:
    - Update P(Ln) via `update_bkt()` (the incorrect answer lowers it)
    - Downgrade `mastery_status` if P(Ln) falls below the mastery bar; requeue for remediation
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
- Store in: `quiz_sessions`

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

### Placement Probe (refines the self-report)

- The first 3 questions of a new thema are served at easy / medium / hard tiers
- Each answer adjusts P(L0) of the thema's concepts by ±0.1, clamped to [0.1, 0.9]
- Runs inside the normal session — no extra UI; the adaptive loop takes over from question 4

# 🔹 Step 6: Concept–Bloom Mapping (Prompt 2)

## 🧠 Logic Flow

**Input**: Thema and Topic from Step 5

**Example**:

```json
{
  "thema": "Photosynthesis",
  "topic": "Light reactions"
}
```

### Prompt 2 Execution

- AI generates a list of atomic concepts under the Thema
- For each concept, assign feasible Bloom levels (based on cognitive task type, not difficulty)
- For each concept, assign a complexity level (Low / Medium / High) → stored in `learning_units.complexity_level`
- Store in `concept_map`
- Each entry links the Thema → Concept → Bloom level
- This becomes the scope for adaptive question generation

# 🔹 Step 7: BKT Initialization (no LLM call)

Initialize BKT parameters per concept in code — no prompt involved:

- **P(L0)**: from the exposure level collected in Step 5 (Unseen 0.2 / Recognized 0.4 / Practiced 0.6 / Mastered 0.8), refined by the placement probe
- **P(T), P(G), P(S)**: retrieved from `bkt_parameter_defaults`, keyed by the concept's `complexity_level` assigned in Step 6 (Prompt 2)

### In the code, apply following logic:

1. Does the user have a profile? (age, education, profession)
2. Has the user been exposed to the Thema before? (`user_thema_exposure`)
3. Look up `bkt_parameter_defaults` by complexity level and seed P(L0) from exposure

# 🔹 Step 8: Question Generation & Validation

**Prompt 3**: Generate questions using:

- Concept–Bloom pairs
- Target `difficulty_tier` (easy / medium / hard), proposed by the LLM
- Current mastery model: P(Ln) from BKT

## 🔹 Generation Pipeline (generate ahead, serve instantly)

Questions are generated ahead of need into a **shared pool per concept–Bloom–difficulty bucket** — never with a live LLM call in the serve path. The `questions` table has no `user_id` / `session_id` column: generation is anonymous and shared across every learner who reaches that bucket. Personalization happens at **selection**, not generation — the serving step picks a bucket-matching question this user hasn't already answered (checked against `user_responses`):

- **Bulk generation**: questions are generated in small batches (~5) per concept–difficulty bucket, one LLM call per batch — prompt tokens amortize across the batch, and the batch is reused by every learner who lands on that bucket. Selection stays per-answer and per-user (adaptive); only generation is batched and shared
- **At session start** (during the session-init screen, ≤2s budget): generate the first batches for the session's concepts in the background, if a bucket's pool is running low
- **While the user answers question N** (20–60s window): top up the buckets the user could land in next (Remediate / Practice / Advance), if their pool is running low
- **Top-ups are triggered by answering, never by a timer** — an idle or abandoned session generates nothing and costs nothing
- **Serving** = reading an already-generated, not-yet-answered-by-this-user question from the shared pool in the `questions` table (<200ms, indexed read)
- **Pool exhausted for this user** (every matching question already answered, or the generator hasn't caught up): fall back to a live LLM call with a "preparing your question…" state — the exception, not the norm

### Session length & ending

- Quiz length may be **time**, **question count**, **both** (ends at whichever hits first), or **no limit**
- An **"End quiz"** control is available in every session at any moment → session closes gracefully and shows results
- **No limit** = open-ended session: generation continues only as the learner keeps answering; the natural endpoint is mastery of the session's concepts
- After ~10 minutes of inactivity the session auto-closes and saves results, shown on return

## 🔹 Step 8A: Question Validation

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
- **Difficulty tier**: Present and one of easy / medium / hard

#### ✅ Technical Validation

- **Language**: Supported and matches user preference
- **Question type**: Valid and supported
- **Metadata**: Complete and consistent

### Implementation

_See `python-functions.md` for the `validate_question()` function implementation._

### Validation Workflow

1. **Generate question** using Prompt 3
2. **Run validation** using checklist above
3. **Log validation results** in `question_validation_log`
4. **If validation passes**: Store in `questions`
5. **If validation fails**: Regenerate or flag for manual review

### Feedback-Based Quality Improvement

- **Use feedback logs** to improve question generation:
  - Score prompt variants based on user ratings
  - Identify weak question types from flag reasons
  - Tune Bloom-level difficulty mappings
  - Optimize generation templates based on feedback patterns
- **Calibrate the generator's difficulty labels** (questions are single-user, so calibration targets the LLM's labeling, not individual questions):
  - Periodically compute observed correct rates from `user_responses` per concept–tier
  - Expected: easy ≈ >80% correct, medium ≈ 40–80%, hard ≈ <40%
  - If a tier drifts (e.g., "easy" questions only 55% correct), adjust the generation prompt or tier mapping

### Store Results

- **Valid questions**: Store in `questions`
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

Invoke function `update_bkt` in order to update:

- BKT: P(Ln) for the concept–Bloom pair
- Store the updated P(Ln) in `concept_progress_tracker.p_ln` (current mastery per pair); the answer itself is already logged in `user_responses` (Step 9)

**Log feedback data**:

- Insert feedback into `question_feedback_log` (normalized design)
- Link feedback to specific `response_id` for audit and tuning
- Use feedback for question quality improvement

_See `python-functions.md` for the `update_bkt()` function implementation._

# 🔹 Step 11: Adaptive Decision Engine

**Purpose**: Decide what question to ask next by combining mastery signals, Bloom level history, and spaced repetition needs. This engine ensures learners are challenged appropriately, reinforced when needed, and periodically reviewed to prevent forgetting.

## 🧠 Decision Flow

### Check for Review Tasks (Spaced Repetition)

- Scan `review_queue` for this user's entries (an entry's presence means a review is due — Step 3A only inserts due pairs, and Step 3D deletes completed ones)
- If found:
  - Select the `concept_id` and `bloom_level` from the review entry
  - Set `decision_type = "Review"`
  - Serve a question from the user's pre-generated buffer (generate via Prompt 3 only if the buffer is empty)
  - After response:
    - Move the entry to `review_queue_archive` and delete it from `review_queue` (Step 3D)
    - Update `mastery_log.last_reinforced = now`
    - Update `fsrs_state` / `next_review_at` with the outcome

### Otherwise, Use Mastery Signals to Guide Selection

Based on the updated P(Ln) for each concept–Bloom pair. The three bands are exhaustive — every P(Ln) value in [0, 1] has a defined action:

**Remediate** (P(Ln) < 0.40, or repeated slips at any level)

- Select the same concept one Bloom level down (or `difficulty_tier = 'easy'` at the lowest Bloom level); scaffolded hints free
- Set `decision_type = "Remediate"`

**Practice** (0.40 ≤ P(Ln) ≤ 0.85)

- Select the same concept–Bloom pair, tier matched to P(Ln): < 0.6 → easy, otherwise medium
- Set `decision_type = "Practice"`

**Advance** (P(Ln) > 0.85)

- Select a higher Bloom level and a harder `difficulty_tier` (or the next weakest concept if the Bloom ladder is done)
- Set `decision_type = "Advance"`

### Track Bloom-Level History per Concept

- Log each assessed Bloom level in `concept_progress_tracker`
- Mastery is declared per concept–Bloom pair, not per concept alone

### Skip Mastered Bloom Levels (Unless in Review Mode)

- If a concept–Bloom pair is mastered and its FSRS predicted recall ≥ 0.90, skip it
- If predicted recall < 0.90, requeue for spaced repetition

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

- P(Ln), Bloom history
- Session performance data
- Learning progression insights

### Declare concept–Bloom pair mastered when:

- P(Ln) ≥ 0.95
- Last 3 answers on this pair correct without hints
- Store in: `mastery_log`

(The 3-clean-answers streak is direct recent evidence; BKT's P(G) already discounts lucky guesses, and the decision bands ensure a high P(Ln) is earned against difficulty-matched questions.)

### Mastery stays honest over time

- After mastery, the pair lives on the FSRS review calendar
- FSRS predicted recall probability is the decay signal — it drives review priority and dashboard "fading" indicators
- A failed review lowers P(Ln) via `update_bkt()` and can downgrade mastery
- This keeps the system adaptive, honest, and pedagogically sound

---

**Mastery is tracked per concept–Bloom level pair.** Each Bloom level represents a distinct cognitive mastery state. Review and decay logic operate independently per Bloom level.
