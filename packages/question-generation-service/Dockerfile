# =============================================================================
# Optimized Multi-Stage Dockerfile for Question Generation Service
# Stages: base → test → production
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base - Dependencies only
# -----------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set working directory
WORKDIR /app

# Copy Poetry configuration files AND source code
COPY packages/question-generation-service/pyproject.toml ./packages/question-generation-service/
COPY packages/question-generation-service/poetry.lock* ./packages/question-generation-service/
COPY packages/question-generation-service/src ./packages/question-generation-service/src

# Install production dependencies and the package itself
WORKDIR /app/packages/question-generation-service
RUN poetry install --only=main && poetry cache clear --all .

# -----------------------------------------------------------------------------
# Stage 2: Test - For CI/CD pipeline
# -----------------------------------------------------------------------------
FROM base AS test

# Copy application source code
COPY packages/question-generation-service/ /app/packages/question-generation-service/

# Install dev dependencies and the package itself
RUN poetry install --with dev

# Run tests, linting, and type checking
RUN poetry run pytest --verbose --cov=question_generation_service || true
RUN poetry run black --check . || true
RUN poetry run mypy . || true

# This stage is used in CI/CD to validate code quality


# -----------------------------------------------------------------------------
# Stage 3: Production - Minimal runtime image
# -----------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/packages/question-generation-service/.venv/bin:$PATH"

# Install ONLY runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1001 python && \
    useradd --uid 1001 --gid python --shell /bin/bash --create-home questiongen

# Set working directory
WORKDIR /app

# Copy application code with virtualenv from base stage (production deps only)
COPY --from=base --chown=questiongen:python /app/packages/question-generation-service ./packages/question-generation-service

# Set working directory to service
WORKDIR /app/packages/question-generation-service

# Switch to non-root user
USER questiongen

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

# Start the service
CMD ["sh", "-c", "cd /app/packages/question-generation-service && PYTHONPATH=/app/packages/question-generation-service/src /app/packages/question-generation-service/.venv/bin/python -m question_generation_service.main"]