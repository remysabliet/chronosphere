# Question Generation Service

AI-powered question generation using the Mistral API.

## Tech Stack

- **Python 3.11+ + FastAPI**
- **Mistral API** — `MISTRAL_MODEL` (large) for extraction/generation quality, `MISTRAL_FAST_MODEL` (small) for lightweight NLU
- **PostgreSQL** for question storage

## Key Features

- AI question generation from text
- Question validation and quality control
- Difficulty tiers (easy/medium/hard), calibrated against observed correct rates
- Multiple question types (MCQ, multi-select MCQ, True/False, Fill-in)

## Wizard Conversation Flow — design intent

The quiz-creation wizard is a chat, and **every free-text message is interpreted by AI, never by keyword parsing**. Three ideas drive the design:

1. **Intent before extraction.** Prompt 1 first classifies each message (`topic` / `greeting_or_chitchat` / `meta_question` / `unintelligible`) and only extracts a thema for real topics. Non-topic messages get a short in-character `reply` generated in the same call (zero extra cost) — so greeting the wizard never produces a "study of greetings" interpretation, and a chit-chat "clarification" never supersedes a pending extraction.
2. **Step-aware answers.** While the sizing question is open, the frontend sends typed text to `/v1/wizard/quiz-length/interpret` (fast model), which reads minutes / question count / unlimited from any phrasing, in any language. Both limits may be set at once — the quiz ends at whichever hits first. A no-clue answer returns a `reply` that responds naturally and steers back to the question.
3. **Generate ahead, serve instantly.** Questions are generated in small batches (~5) per concept–difficulty bucket in the background; top-ups are triggered by the learner _answering_ (an idle session generates nothing and costs nothing), and serving is a DB read. Every session has an "End quiz" exit to the results screen; unlimited sessions rely on that plus an idle auto-close.

Full workflow: `docs/product/main-workflow.md` (Step 8) and `docs/product/adaptive-engine-review.md` at the repo root.

## API Endpoints

```
POST /v1/thema/extract                    # Interpret raw input (intent + thema/topics)
POST /v1/thema/{id}/refine                # Re-interpret with a learner clarification
POST /v1/thema/{id}/confirm               # Confirm the interpretation before generation
POST /v1/thema/{id}/exposure               # Answer the exposure question -> BKT init
POST /v1/concepts/map                     # Map thema/topics to concept–Bloom pairs
POST /v1/wizard/quiz-length/interpret     # Read a quiz size from free text (fast model)
POST /v1/questions/generate               # Generate + validate a question batch (Step 8/8A)
```

Interactive docs: `http://localhost:8001/scalar` (or `/docs`).

## Development

```bash
uv sync
.venv/bin/uvicorn question_generation_service.main:app --reload --port 8001
```

## Testing

Uses `uv`. No env vars needed for unit tests — `tests/conftest.py` injects fake values before any module is imported.

```bash
# Install dev dependencies (first time)
uv sync --dev

# Run unit tests
uv run pytest tests/unit/

# With coverage report (fails if < 80%)
uv run pytest tests/unit/ --cov=question_generation_service --cov-report=term-missing --cov-fail-under=80

# Single file or test
uv run pytest tests/unit/test_thema_router.py -v
uv run pytest tests/unit/test_thema_service.py::test_resolved_when_clear_winner -v
```

Integration tests require a running PostgreSQL instance:

```bash
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/memosphere_test" \
  uv run pytest tests/integration/
```

### Live AI pipeline test (real Mistral, real cost)

`tests/integration/test_live_ai_pipeline.py` drives the whole pipeline — thema
extraction, concept mapping, exposure/BKT init, question generation, and the
judge — against the **real** Mistral API instead of a mock, and prints every
generated question so you can actually read and judge the content. It's
skipped by default (needs a real `MISTRAL_API_KEY`, costs real credits) —
opt in explicitly:

```bash
RUN_LIVE_MISTRAL_TESTS=1 DATABASE_URL="postgresql://memosphere:memosphere_secure_dev_2025!@localhost:5432/memosphere_test" \
  uv run pytest tests/integration/test_live_ai_pipeline.py -v -s
```

`-s` is required to see the printed output. Override the topic with
`LIVE_AI_TEST_INPUT="..."` if you want to try something other than the
default. Runs deliberately slowly (spaced-out calls) — Mistral's rate limit
is tight enough to trip within a single run otherwise.

## Port: 8001
