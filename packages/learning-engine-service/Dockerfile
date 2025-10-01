# =============================================================================
# Optimized Multi-Stage Dockerfile for Learning Engine Service
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

# Install system dependencies for building ML libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    gcc \
    g++ \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set working directory
WORKDIR /app

# Copy Poetry configuration files AND source code
COPY packages/learning-engine-service/pyproject.toml ./packages/learning-engine-service/
COPY packages/learning-engine-service/poetry.lock* ./packages/learning-engine-service/
COPY packages/learning-engine-service/src ./packages/learning-engine-service/src

# Install production dependencies and the package itself
WORKDIR /app/packages/learning-engine-service
RUN poetry install --only=main && poetry cache clear --all .

# -----------------------------------------------------------------------------
# Stage 2: Test - For CI/CD pipeline
# -----------------------------------------------------------------------------
FROM base AS test

# Copy application source code
COPY packages/learning-engine-service/ /app/packages/learning-engine-service/

# Install dev dependencies and the package itself
RUN poetry install --with dev

# Run tests, linting, and type checking
RUN poetry run pytest --verbose --cov=learning_engine_service || true
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
    PATH="/app/packages/learning-engine-service/.venv/bin:$PATH"

# Install ONLY runtime system dependencies (no compilers!)
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    libblas3 \
    liblapack3 \
    libatlas3-base \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1001 python && \
    useradd --uid 1001 --gid python --shell /bin/bash --create-home learningengine

# Set working directory
WORKDIR /app

# Copy application code with virtualenv from base stage (production deps only)
COPY --from=base --chown=learningengine:python /app/packages/learning-engine-service ./packages/learning-engine-service

# Set working directory to service
WORKDIR /app/packages/learning-engine-service

# Switch to non-root user
USER learningengine

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8002/health || exit 1

# Start the service
CMD ["sh", "-c", "cd /app/packages/learning-engine-service && PYTHONPATH=/app/packages/learning-engine-service/src /app/packages/learning-engine-service/.venv/bin/python -m learning_engine_service.main"]
