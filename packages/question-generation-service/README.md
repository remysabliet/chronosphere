# Question Generation Service

AI-powered question generation using Mistral Large API.

## Tech Stack

- **Python 3.11+ + FastAPI**
- **Mistral Large API** for AI generation
- **PostgreSQL** for question storage

## Key Features

- AI question generation from text
- Question validation and quality control
- IRT metadata assignment
- Multiple question types (MCQ, True/False, Fill-in)

## API Endpoints

```
POST /v1/thema/extract              # Extract thema/topics from raw input
POST /v1/thema/{id}/confirm         # Confirm the interpretation before generation
POST /questions/generate            # Generate questions from text
GET  /questions/:id                 # Get specific question
POST /validate/question             # Validate question quality
POST /irt/calibrate                 # Calibrate IRT parameters
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

## Port: 8001

Best practice in teams (common compromise)
Use Poetry as the source of truth

So: Poetry is “better” for development and consistency, and requirements.txt is mainly a distribution format when required by your infrastructure.

Export requirements.txt for deployment if needed:
poetry export -f requirements.txt --output requirements.txt --without-hashes
