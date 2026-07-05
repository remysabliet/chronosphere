# Memosphere Functional Specification

## 1. System Overview

**Memosphere** is an AI-powered adaptive learning platform that transforms text into interactive, multimedia-rich quiz experiences using BKT (Bayesian Knowledge Tracing) and IRT (Item Response Theory) algorithms combined with mnemonic techniques for optimal retention.

**Core Value Proposition**: Convert any text into adaptive, multi-sensory learning experiences (visual, auditory, interactive) that identify knowledge gaps, track mastery, and implement spaced repetition for long-term retention.

---

## 2. Interactive Learning Modalities

### 2.1 Question Types & Formats

| Type                        | Description                      | Cognitive Benefits       | Mnemonic Technique   |
| --------------------------- | -------------------------------- | ------------------------ | -------------------- |
| **Multiple Choice (MCQ)**   | Traditional 2-5 option questions | Recall, recognition      | Association          |
| **True/False**              | Binary correctness judgment      | Quick validation         | Pattern recognition  |
| **Fill-in-the-Blank**       | Complete missing words/phrases   | Active recall            | Contextual cues      |
| **Memocards (Flashcards)**  | Front/back card with multimedia  | Visual + auditory memory | Imagery + repetition |
| **Listening Comprehension** | Audio-based questions            | Auditory learning        | Sound association    |
| **Image Recognition**       | Visual identification tasks      | Visual memory            | Imagery              |
| **Matching**                | Pair concepts/terms              | Relationship learning    | Association          |
| **Ordering/Sequencing**     | Arrange items in correct order   | Process understanding    | Chunking             |
| **Speaking (Future)**       | Pronunciation/oral response      | Production practice      | Motor memory         |

---

### 2.2 Memocard System (Flashcard-Based Learning)

**Function**: Spaced repetition flashcards with multimedia enhancement

**Components**:

#### Front of Card (Question Side)

- Text-based question/prompt
- Optional image (AI-generated or curated)
- Optional audio pronunciation (text-to-speech)
- Visual cues (icons, colors) for context

#### Back of Card (Answer Side)

- Correct answer with explanation
- Mnemonic aids:
  - Related imagery (vivid, memorable visuals)
  - Audio clips (pronunciation, sound effects)
  - Association hints (link to known concepts)
  - Memory palace suggestions
- Difficulty self-rating (Easy/Good/Hard)

**User Interactions**:

1. Card presented (front side)
2. User recalls answer mentally or speaks aloud
3. User flips card to reveal answer
4. User rates difficulty → adjusts next review interval
5. BKT updated: the rating maps to a response score fed through `update_bkt()`

**Spaced Repetition Schedule**:

- Intervals are computed per card by FSRS from the Again/Hard/Good/Easy rating history
- **Again**: also re-queued later in the same session

**Business Rules**:

- Memocards used for "Remembering" Bloom level primarily
- Each card tagged with concept, Bloom level, difficulty tier
- Cards can be favorited, archived, or flagged
- Deck size: 10-50 cards per session

---

### 2.3 Multimedia Question Enhancement

**Function**: Add sensory learning aids to all question types

#### Visual Components

**AI-Generated Images**:

- Generate relevant visuals using Mistral API or DALL-E integration
- Image types: diagrams, concept illustrations, mnemonic imagery
- Stored in Amazon S3, served via CloudFront CDN
- Alt text for accessibility

**Use Cases**:

- Vocabulary learning (image + word)
- Historical events (timeline visuals)
- Scientific concepts (diagrams, charts)
- Geography (maps, landmarks)

**Technical Implementation**:

```json
{
  "question_id": "uuid",
  "visual_aids": [
    {
      "type": "image",
      "url": "s3://bucket/images/photosynthesis-diagram.png",
      "alt_text": "Diagram showing light and dark reactions",
      "position": "inline", // or "hint", "answer"
      "mnemonic_value": 0.8 // AI-generated relevance score
    }
  ]
}
```

#### Audio Components

**Text-to-Speech (TTS)**:

- Question read-aloud for accessibility
- Pronunciation guides for vocabulary
- Service: Amazon Polly or Google Cloud TTS
- Languages: en, fr, es, de, ja, zh

**Audio Cues**:

- Sound effects for correct/incorrect answers
- Background music for focus (optional, user toggle)
- Mnemonic sounds (e.g., rhymes, jingles for formulas)

**Listening Comprehension Questions**:

- Play audio clip (story, conversation, lecture)
- Ask questions about content
- Adjustable playback speed (0.5x to 2x)
- Transcript available as hint

**Technical Implementation**:

```json
{
  "question_id": "uuid",
  "audio_aids": [
    {
      "type": "tts",
      "text": "What is the powerhouse of the cell?",
      "language": "en-US",
      "voice": "neural", // or "standard"
      "auto_play": false
    },
    {
      "type": "listening_clip",
      "url": "s3://bucket/audio/photosynthesis-lecture.mp3",
      "duration_seconds": 45,
      "transcript": "Photosynthesis is the process...",
      "playback_controls": true
    }
  ]
}
```

---

### 2.4 Interactive Quiz Formats

#### Game-Based Learning

**Timed Challenges**:

- Answer as many questions as possible in 2 minutes
- Streak bonuses for consecutive correct answers
- Leaderboard for competitive users

**Concept Battles**:

- Two concepts compete (e.g., Mitochondria vs Chloroplast)
- Answer questions for each, higher score "wins"
- Gamifies review of multiple concepts

**Progress Quests**:

- Narrative-driven learning paths
- Unlock new "levels" (Bloom levels) by mastering concepts
- Visual progress bar and achievement badges

#### Adaptive Hint System

**Function**: Scaffold learning with progressive hints

**Hint Levels**:

1. **Level 0** (No Hint): Full question, no aids
2. **Level 1** (Context Hint): Related concept or category
3. **Level 2** (Elimination): Remove 1-2 incorrect options
4. **Level 3** (Partial Answer): First letter or partial info
5. **Level 4** (Full Explanation): Complete answer with reasoning

**Business Rules**:

- Hints available after 15 seconds or user request
- Using hints reduces P(Ln) gain (partial credit)
- Hint usage tracked for adaptive difficulty
- Free hints for concepts with P(Ln) < 0.4

---

## 3. Core Learning Workflow

### 3.1 User Onboarding (Steps 1-2)

**Function**: Create user account and establish learning preferences

**Inputs**:

- Email/OAuth credentials
- Profile: age, profession, education level (optional)
- **Learning Preferences**:
  - Preferred question types (MCQ, memocards, listening)
  - Multimedia preferences (images, audio, text-only)
  - Session duration (5min, 15min, 30min, custom)
  - Daily goal (questions per day)
  - Accessibility needs (screen reader, large text, TTS)

**Outputs**:

- User profile created in `users` table
- Learning preferences stored
- Default memocard decks created
- Initial BKT parameters set

**Business Rules**:

- Default: All question types enabled
- Multimedia auto-enabled, user can disable per type
- GDPR consent required for personalization

---

### 3.2 Spaced Repetition Review (Step 3)

**Function**: Prevent knowledge decay through scheduled multimedia reviews

**Trigger**: Daily batch job or user login

**Process**:

1. For each concept–Bloom pair in `mastery_log`, compute FSRS predicted recall from `fsrs_state`
2. Queue pairs with predicted recall < 0.90 (or `next_review_at ≤ NOW()`)
3. Generate review queue prioritizing:
   - Lowest predicted recall (highest priority)
   - Due memocards (FSRS intervals)
   - Concepts with high slip count
4. **Select review format** based on concept type:
   - Visual concepts → Image-based questions or memocards
   - Vocabulary/pronunciation → Listening comprehension
   - Procedural knowledge → Ordering/sequencing
5. Present "Memory Refresh" module

**Outputs**:

- Review queue with mixed question types
- Multimedia assets pre-loaded for smooth UX
- Estimated review time displayed

**Business Rules**:

- Review sessions shorter than learning sessions (10-15 min)
- Maximum 20 memocards per review session
- Audio clips auto-played once, user can replay

---

### 3.3 Quiz Session Initialization (Steps 4-7)

**Function**: Start adaptive, multimedia learning session

**Inputs**:

- User ID
- Keywords/thema (e.g., "Japanese JLPT1", "Photosynthesis")
- **Content Type** (new field):
  - Text input (paste article/notes)
  - URL (scrape web content)
  - PDF upload (extract text)
  - Audio file (transcribe + generate questions)
- Bloom level range (optional)
- Session type: "learning", "review", "assessment", "memocard-drill"
- **Multimedia preferences** for this session

**Process**:

#### Step 5: Thema Extraction + Content Analysis

- **AI Prompt 1**: Extract Thema, Topic, and **identify multimedia opportunities**
  - "This content would benefit from visual diagrams" → Generate images
  - "Vocabulary-heavy content" → Create memocards with audio
  - "Process-based learning" → Suggest ordering questions
- Check `user_thema_exposure` for prior exposure
- Determine optimal question type mix based on content

#### Step 6: Concept Mapping + Multimedia Asset Planning

- **AI Prompt 2**: Generate atomic concepts + assign Bloom levels
- **NEW**: For each concept, identify mnemonic techniques:
  - `mnemonic_type`: "imagery", "audio", "association", "chunking"
  - `multimedia_assets_needed`: ["diagram", "pronunciation_audio"]
- Store in `learning_units` with `multimedia_metadata` JSON field

#### Step 7: BKT Initialization + Question Type Selection

- Retrieve default BKT parameters
- **NEW**: Determine question type distribution:
  - Remembering → 60% memocards, 40% MCQ
  - Understanding → 70% MCQ, 30% fill-in-blank
  - Applying → 50% MCQ, 30% ordering, 20% matching
  - Analyzing+ → 80% MCQ, 20% open-ended (text)

**Outputs**:

- Session created with `multimedia_enabled = true`
- Asset generation queue populated
- Question type distribution plan
- Estimated session time (accounts for audio playback)

**Business Rules**:

- Multimedia assets generated asynchronously (don't block session start)
- Fallback to text-only if asset generation fails
- User can disable multimedia mid-session

---

### 3.4 Question Generation & Multimedia Enhancement (Step 8)

**Function**: Generate interactive, multimedia-rich questions

**Inputs**:

- Concept-Bloom pairs
- Current mastery (P(Ln))
- Mnemonic technique recommendations
- User multimedia preferences

**Process**:

1. **Select Question Type** based on:
   - Bloom level (canonical 6-level taxonomy, ascending cognitive demand — see distribution above):
     1. Remembering
     2. Understanding
     3. Applying
     4. Analyzing
     5. Evaluating
     6. Creating
   - User preferences
   - Mnemonic suitability
   - Prior question type history (avoid repetition)

2. **Generate Base Question**:
   - **AI Prompt 3**: Create question with specified type
   - Include mnemonic hints in prompt:
     - "Create vivid imagery for this concept"
     - "Include phonetic pronunciation"
     - "Suggest association with everyday objects"

3. **Generate Multimedia Assets**:

   **For Visual Learners**:
   - **AI Prompt 3a**: Generate image description
   - Call DALL-E or Mistral image gen: "Create diagram showing..."
   - Store in S3, cache URL in question JSON

   **For Auditory Learners**:
   - Extract key terms requiring pronunciation
   - Call Amazon Polly TTS for audio files
   - For language learning: Generate native speaker audio

   **For Memocards**:
   - Front: Question + optional image
   - Back: Answer + mnemonic imagery + audio
   - Assign initial FSRS memory state

4. **Assign Difficulty Tier**:
   - `difficulty_tier`: easy / medium / hard, proposed by the LLM at generation time
   - Labeling accuracy monitored via observed correct rates in `user_responses` (per concept–tier); drift feeds back into prompt tuning

5. **Validate Question**:
   - Content quality checks
   - Multimedia asset quality (image clarity, audio quality)
   - Accessibility compliance (alt text, transcripts)

**Outputs**:

- Interactive question stored in `questions` table
- Multimedia assets in S3 with CDN URLs
- Question type and mnemonic metadata
- Validation log with multimedia quality scores

**Technical Schema**:

```json
{
  "question_id": "uuid",
  "question_type": "memocard",
  "question_text": "What is the process by which plants convert light to energy?",
  "correct_answer": "Photosynthesis",
  "mnemonic_aids": {
    "imagery": {
      "url": "s3://bucket/photosynthesis-plant-sunlight.png",
      "description": "Vivid image of plant absorbing sunlight",
      "ai_generated": true
    },
    "audio": {
      "pronunciation_url": "s3://bucket/tts/photosynthesis-en.mp3",
      "mnemonic_sound": "s3://bucket/sounds/camera-flash.mp3", // "Photo" = flash
      "explanation_audio": "s3://bucket/tts/photosynthesis-explanation.mp3"
    },
    "association": "Think: 'Photo' (light) + 'synthesis' (making) = making with light",
    "memory_palace": "Imagine a plant in your kitchen synthesizing energy from window light"
  },
  "card_face": {
    "front": {
      "text": "What is the process by which plants convert light to energy?",
      "image_url": "s3://bucket/plant-question.png",
      "audio_url": "s3://bucket/tts/question-readout.mp3"
    },
    "back": {
      "text": "Photosynthesis",
      "explanation": "Photo = light, synthesis = making. Plants make energy from light.",
      "image_url": "s3://bucket/photosynthesis-process-diagram.png",
      "audio_url": "s3://bucket/tts/answer-explanation.mp3"
    }
  },
  "accessibility": {
    "alt_text": "Diagram showing light reactions in chloroplast",
    "transcript": "Full text transcript of all audio",
    "high_contrast_mode": true,
    "screen_reader_optimized": true
  }
}
```

**Business Rules**:

- Maximum 2 images per question (avoid cognitive overload)
- Audio clips max 60 seconds
- All multimedia optional, user can disable
- Asset generation timeout: 5 seconds (fallback to text)

---

### 3.5 Learner Interaction (Steps 9-10)

**Function**: Deliver interactive question, collect response, update models

**User Experience Flow**:

#### Memocard Flow

1. **Card Presented** (front):
   - Display question text
   - Show image (if available)
   - Auto-play audio (if user preference enabled)
   - "Flip Card" or spacebar to reveal answer
2. **Card Flipped** (back):
   - Show answer with explanation
   - Display mnemonic aids (imagery, association)
   - Play pronunciation audio
   - "How difficult was this?" → Easy / Good / Hard / Again
3. **Model Update**:
   - Rating maps to a response score fed through `update_bkt()` — never a direct P(Ln) adjustment: Again = 0.0, Hard = 0.4, Good = 0.8, Easy = 1.0
   - Review scheduling: FSRS computes the next review date from the rating; Again → also re-queued this session

#### MCQ/Interactive Flow

1. **Question Presented**:
   - Display question with multimedia
   - Show answer options
   - Timer (optional, user preference)
   - Hint button (available after 15s)
2. **User Selects Answer**:
   - Visual feedback (green/red animation)
   - Play sound effect (correct chime / incorrect buzz)
   - Show explanation with multimedia
   - Display mnemonic aid for incorrect answers
3. **Track Response**:
   - Response time
   - Confidence level (self-reported or inferred from time)
   - Hints used
   - Multimedia engagement (played audio, viewed image)

#### Listening Comprehension Flow

1. **Audio Clip Played**:
   - Progress bar with playback controls
   - Replay button (max 2 replays)
   - Speed control (0.5x, 1x, 1.5x)
2. **Question After Audio**:
   - Questions based on clip content
   - Transcript available as hint (penalty applied)
3. **Track Audio Engagement**:
   - Number of replays
   - Speed used
   - Transcript accessed (yes/no)

**Process**:

#### Step 9: Response Collection

- Log in `user_responses` table with:
  - `question_type`: memocard, MCQ, listening, etc.
  - `multimedia_used`: JSON array of assets engaged
  - `hints_used`: count and types
  - `audio_replays`: count
  - `self_rated_difficulty`: for memocards
  - `response_time`: actual time spent
  - `confidence_level`: Low/Medium/High

#### Step 10: Model Update

- **Update BKT**: Call `update_bkt()` with a response score — all evidence goes through the formula, nothing adjusts P(Ln) directly:
  - Correct without hints → 1.0; incorrect → 0.0
  - Hint-assisted correct answer → 0.5
  - Memocard self-rating → Again = 0.0, Hard = 0.4, Good = 0.8, Easy = 1.0
  - Audio replays: no P(Ln) effect (tracked for personalization only)
- **Update Memocard Schedule**:
  - FSRS computes the next interval from the rating
  - Store `fsrs_state` and `next_review_at`

**Outputs**:

- Response logged with multimedia engagement metrics
- P(Ln) updated per concept
- Memocard schedule updated
- Feedback stored

**Business Rules**:

- Skipped questions → no model update
- Timeout (2 min) → marked as "no response"
- Multimedia engagement tracked for personalization
- Users can replay audio questions once for free

---

### 3.6 Adaptive Decision Engine (Step 11)

**Function**: Select next question type and multimedia approach

**Decision Logic**:

1. **Check Review Queue**
   - Due memocards have highest priority
   - Expired mastery → review with same question type that worked before

2. **Select Question Type** based on:
   - **Bloom Level**:
     - Remembering → Prefer memocards (70%)
     - Understanding+ → Prefer MCQ/interactive (70%)
   - **Learning Style** (inferred from engagement):
     - High image view rate → More visual questions
     - High audio replay rate → More listening questions
     - Fast response times → More game-based challenges
   - **Fatigue Management**:
     - After 10 text-heavy questions → Insert memocard break
     - After 20 questions → Insert listening comprehension (change of pace)
     - Session duration >30 min → More interactive/gamified questions

3. **Adapt Multimedia Usage**:
   - If user skips images repeatedly → Reduce image generation
   - If audio engagement high → Prioritize listening questions
   - If hints frequently used → More scaffolded questions

4. **Adaptive Difficulty** (exhaustive bands, no gaps):
   - Remediate (P(Ln) < 0.40, or repeated slips) → Lower Bloom, easier tier, free hints
   - Practice (0.40 ≤ P(Ln) ≤ 0.85) → Same level, tier matched to P(Ln)
   - Advance (P(Ln) > 0.85) → Higher Bloom, harder tier
   - Mastered (P(Ln) ≥ 0.95 + last 3 answers clean) → declared mastered, moves to review schedule

**Inputs**:

- Current P(Ln)
- Question type history (avoid 5+ consecutive same type)
- Multimedia engagement metrics
- Session fatigue indicators (time, question count)

**Outputs**:

- Next question ID and type
- Multimedia assets to pre-load
- Decision rationale logged

**Business Rules**:

- Maximum 10 memocards in a row (prevent monotony)
- Minimum 20% multimedia questions per session
- Interactive questions preferred when P(Ln) plateaus

---

### 3.7 Session Completion & Analytics (Steps 12-13)

**Function**: Finalize session with multimedia insights

**Process**:

#### Step 12: Session Analytics

- **Performance Metrics**:
  - Accuracy by question type
  - Average response time per type
  - Hints used vs accuracy
  - Audio replays vs correctness
- **Engagement Metrics**:
  - Multimedia assets viewed/played
  - Question types completed
  - User preferences (auto-play audio, image display)
- **Memocard Metrics**:
  - Cards reviewed, mastered, remaining
  - Self-rating distribution (Easy/Good/Hard/Again)
  - Deck completion rate

#### Step 13: Mastery Declaration + Recommendations

- **Declare Mastery** (existing criteria)
- **Generate Personalized Feedback**:
  - "You engaged most with visual diagrams" (if image engagement high)
  - "Try more memocards for vocabulary" (if Remembering level struggles)
  - "Listening comprehension improved 20% this session"
- **Memocard Deck Suggestions**:
  - "Create a deck for weak concepts?"
  - "Review 15 due cards tomorrow"

**Outputs**:

- Session summary with multimedia breakdown
- Learning style insights
- Memocard review schedule
- Recommended question types for next session

**Business Rules**:

- Sessions with <5 questions don't update preferences
- Multimedia engagement trends updated after 3+ sessions

---

## 4. Memocard System Details

### 4.1 Memocard Creation

**Sources**:

1. **Auto-Generated** from concepts during quiz sessions
2. **User-Created** from scratch
3. **Imported** from Anki, Quizlet, CSV

**Auto-Generation Process**:

- After mastering concept → "Create memocard for review?"
- AI generates front/back with multimedia
- User can edit before saving

**Storage Schema**:

```sql
CREATE TABLE memocards (
  card_id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  concept_id UUID,
  deck_id UUID,
  front_text TEXT NOT NULL,
  front_image_url TEXT,
  front_audio_url TEXT,
  back_text TEXT NOT NULL,
  back_image_url TEXT,
  back_audio_url TEXT,
  mnemonic_aids JSON, -- {imagery, audio, association, memory_palace}
  fsrs_state JSON, -- FSRS memory state (stability, difficulty, ...)
  next_review_at TIMESTAMP,
  created_at TIMESTAMP,
  last_reviewed_at TIMESTAMP
);
```

---

### 4.2 Memocard Decks

**Function**: Organize cards by theme

**Default Decks**:

- "Weak Areas" (auto-populated from low P(Ln) concepts)
- "Daily Review" (due cards across all decks)
- "Favorites" (user-starred cards)
- Custom decks (user-created)

**Deck Settings**:

- Cards per session (10-50)
- New cards per day (5-20)
- Review order: Due date, random, manual
- Multimedia preferences per deck

---

### 4.3 Spaced Repetition Algorithm (FSRS)

**Function**: Optimal review intervals for long-term retention

**Implementation**: `py-fsrs` Python library — the modern successor to SM-2, fit to hundreds of millions of real reviews (used by Anki)

- Each card and each concept–Bloom pair keeps a small `fsrs_state` (a few floats), updated after every review
- Again / Hard / Good / Easy ratings map directly onto FSRS's four grades
- FSRS outputs both the next review date and the current predicted recall probability — the single decay signal used across the system (review priority, dashboard "fading" indicators)

**Business Rules**:

- Minimum interval: 1 day
- Maximum interval: 365 days (1 year)

---

## 5. Multimedia Asset Management

### 5.1 Asset Generation Pipeline

**Workflow**:

1. Question generated → Identify multimedia needs
2. Add to generation queue (Redis)
3. Background worker processes queue:
   - **Images**: Call Mistral/DALL-E API
   - **Audio**: Call Amazon Polly TTS
   - **Diagrams**: Use Mermaid.js or PlantUML
4. Upload to S3, store URL in database
5. Invalidate CloudFront cache if updated

**Performance**:

- Target: <2 seconds for TTS, <5 seconds for images
- Fallback: Serve question without assets if timeout
- Retry logic: 3 attempts with exponential backoff

---

### 5.2 CDN Strategy

**Amazon CloudFront**:

- Global edge caching for multimedia assets
- Cache TTL: 7 days (images), 30 days (audio)
- Gzip compression for text assets
- Lazy loading for images (IntersectionObserver)

**Cost Optimization**:

- Generate assets once, reuse across users
- Compress images (WebP format, 80% quality)
- Audio: MP3 format, 64kbps bitrate

---

### 5.3 Accessibility Compliance

**WCAG 2.1 AA Standards**:

- All images have alt text (AI-generated + human-reviewed)
- Audio transcripts available
- Keyboard navigation for all interactions
- Screen reader support (ARIA labels)
- Color contrast ratios >4.5:1
- Captions for listening comprehension audio

**User Preferences**:

- High contrast mode
- Large text (1.5x, 2x)
- Audio-only mode (no images)
- Text-only mode (no multimedia)

---

## 6. Learning Style Personalization

### 6.1 Automatic Detection

**Metrics Tracked**:

- Image view rate (% of images opened)
- Audio play rate (% of audio clips played)
- Response time by question type
- Hint usage by question type
- Self-reported difficulty by modality

**Engagement Preference Detection** (after 50+ questions):

- High image engagement → prefers visual formats
- High audio engagement → prefers listening formats
- Fast responses on interactive/game formats → prefers interactive formats
- Low multimedia engagement → prefers text-only

Note: format preferences drive enjoyment and engagement, not learning effectiveness. Formats are matched to _content type_ (vocabulary → audio, processes → sequencing) and to engagement — never presented as "you learn better with X".

**Personalization Actions**:

- Adjust question type distribution
- Increase/decrease multimedia asset generation
- Recommend memocard decks to users with high image engagement
- Suggest listening practice to users with high audio engagement

---

### 6.2 Manual Preferences

**User Settings**:

- Default question types (multi-select)
- Multimedia preferences (images, audio, both, none)
- Auto-play audio (yes/no)
- Mnemonic type preferences (imagery, association, chunking)
- Session structure (% memocards, % MCQ, % listening)

---

## 7. Gamification & Engagement

### 7.1 Achievements & Badges

- **Memocard Master**: Review 100 cards
- **Streak King**: 7-day daily learning streak
- **Multimedia Maven**: Engage with 50 images/audio clips
- **Listening Pro**: Complete 20 listening comprehension questions
- **Quick Thinker**: Average response time <5 seconds

---

### 7.2 Progress Visualization

- **Heatmap Calendar**: Daily activity (GitHub-style)
- **Concept Mastery Map**: Visual graph of concept relationships
- **Bloom Pyramid**: Progress through Bloom levels per concept
- **Memocard Deck Progress**: Circular progress bars per deck

---

## 8. Technical Requirements

### 8.1 Performance SLAs

| Metric                                                          | Target                |
| --------------------------------------------------------------- | --------------------- |
| Question serving (from pre-generated buffer)                    | <200ms                |
| Background question generation (LLM, async, hidden by pipeline) | 1–10s                 |
| Multimedia asset generation (async)                             | <2s images, <5s total |
| TTS audio generation                                            | <1s per sentence      |
| Image loading (CDN)                                             | <500ms                |
| Memocard flip animation                                         | <100ms                |
| Session initialization                                          | <2s                   |

---

### 8.2 Storage Requirements

**Per User (Estimated)**:

- Profile data: 5 KB
- Response history (1 year): 50 KB
- Memocards (100 cards): 20 KB text + 5 MB multimedia
- **Total per user**: ~5-10 MB

**System-Wide**:

- Question bank: 100K questions × 10 KB = 1 GB text
- Multimedia assets: 100K questions × 50 KB = 5 GB (images/audio)
- **Total MVP**: ~10 GB database + 20 GB S3

---

### 8.3 Multimedia Formats

**Images**:

- Format: WebP (primary), PNG (fallback)
- Max size: 500 KB
- Dimensions: 800×600px (responsive)

**Audio**:

- Format: MP3
- Bitrate: 64 kbps (TTS), 128 kbps (music/sound effects)
- Max duration: 60 seconds per clip

**Video** (Future Phase):

- Format: MP4 (H.264)
- Max size: 10 MB
- Max duration: 2 minutes

---

## 9. User Roles & Access

### 9.1 Role-Specific Features

| Role                | Memocards         | Multimedia              | Question Types | Analytics           |
| ------------------- | ----------------- | ----------------------- | -------------- | ------------------- |
| **Learner**         | Full access       | Full access             | All types      | Personal only       |
| **Admin**           | Full + moderation | Full + asset management | All types      | System-wide         |
| **Moderator**       | Review flagged    | Approve/reject assets   | Review all     | Quality metrics     |
| **Content Creator** | Create/edit       | Upload/generate         | Create custom  | Content performance |
| **Analyst**         | View only         | View only               | View only      | Full reports        |

---

## 10. MVP Feature Priorities

### Phase 1 (Must Have)

- ✅ MCQ, True/False, Fill-in-blank questions
- ✅ Memocards with text front/back
- ✅ AI-generated images (for key concepts)
- ✅ Text-to-speech audio (basic TTS)
- ✅ FSRS spaced repetition for memocards
- ✅ Basic hint system
- ✅ Session analytics

### Phase 2 (Should Have)

- ✅ Listening comprehension questions
- ✅ Advanced mnemonic aids (imagery, association)
- ✅ Audio pronunciation for vocabulary
- ✅ Learning style detection
- ✅ Gamification (badges, streaks)
- ✅ Matching and ordering questions

### Phase 3 (Nice to Have)

- Speaking practice (speech recognition)
- Video-based questions
- AR/VR memory palace experiences
- Social features (shared decks, leaderboards)
- Custom mnemonic device creation tools

---

## 11. Success Metrics

### 11.1 Learning Effectiveness

- **Target**: 85%+ retention on memocard reviews
- **Target**: 70%+ concepts mastered within 5 sessions
- **Target**: 30%+ improvement on weak areas after multimedia intervention

### 11.2 Engagement

- **Target**: 20+ minutes average session (with multimedia)
- **Target**: 75%+ users engage with multimedia assets
- **Target**: 50+ memocards created per active user
- **Target**: 4.5+ stars average satisfaction

### 11.3 Multimedia Metrics

- **Target**: <2s average multimedia load time
- **Target**: 80%+ multimedia asset usage rate
- **Target**: 90%+ audio clip completion rate
- **Target**: 70%+ image view rate

---

## 12. Accessibility & Compliance

- **WCAG 2.1 AA** compliant
- **GDPR** compliant (EU users)
- **COPPA** compliant (under-13 users, if applicable)
- **ADA** compliant (US accessibility)
- Multi-language support (UI + content)
- Offline mode for memocards (PWA)
