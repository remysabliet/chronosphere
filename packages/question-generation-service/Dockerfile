# =============================================================================
# Ultra-Optimized Multi-Stage Dockerfile for Question Generation Service
# Optimized for production with security and performance best practices
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base - Dependencies and workspace setup
# -----------------------------------------------------------------------------
  FROM python:3.11-slim AS base

  # Set environment variables
  ENV PYTHONUNBUFFERED=1 \
      PYTHONDONTWRITEBYTECODE=1 \
      PIP_NO_CACHE_DIR=1 \
      PIP_DISABLE_PIP_VERSION_CHECK=1
  
  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      build-essential \
      curl \
      libpq-dev \
      gcc \
      && rm -rf /var/lib/apt/lists/*
  
  # Set working directory
  WORKDIR /app
  
  # Copy Poetry configuration
  COPY packages/question-generation-service/pyproject.toml ./packages/question-generation-service/
  COPY packages/question-generation-service/poetry.lock* ./packages/question-generation-service/
  
  # Install Poetry
  RUN pip install poetry==1.7.1
  
  # Configure Poetry
  ENV POETRY_NO_INTERACTION=1 \
      POETRY_VENV_IN_PROJECT=1 \
      POETRY_CACHE_DIR=/tmp/poetry_cache
  
  # Install dependencies
  WORKDIR /app/packages/question-generation-service
  RUN poetry install --only=main && poetry cache clear --all .
  
  # -----------------------------------------------------------------------------
  # Stage 2: Build - Application setup
  # -----------------------------------------------------------------------------
  FROM base AS build
  
  # Copy application source code
  COPY packages/question-generation-service/ ./packages/question-generation-service/
  
  # Install development dependencies for building
  RUN poetry install --with dev
  
  # Export requirements for production
  RUN poetry export --format=requirements.txt --output=requirements.txt --without-hashes
  
  # -----------------------------------------------------------------------------
  # Stage 3: Production - Minimal runtime image
  # -----------------------------------------------------------------------------
  FROM python:3.11-slim AS production
  
  # Set environment variables
  ENV PYTHONUNBUFFERED=1 \
      PYTHONDONTWRITEBYTECODE=1 \
      PATH="/app/.venv/bin:$PATH"
  
  # Install only runtime system dependencies
  RUN apt-get update && apt-get install -y \
      curl \
      libpq5 \
      && rm -rf /var/lib/apt/lists/* \
      && apt-get clean
  
  # Create non-root user for security
  RUN groupadd --gid 1001 python && \
      useradd --uid 1001 --gid python --shell /bin/bash --create-home questiongen
  
  # Set working directory
  WORKDIR /app
  
  # Copy requirements and install Python dependencies
  COPY --from=build /app/packages/question-generation-service/requirements.txt ./requirements.txt
  RUN pip install --no-cache-dir --user -r requirements.txt
  
  # Copy application code
  COPY --from=build --chown=questiongen:python /app/packages/question-generation-service ./packages/question-generation-service
  
  # Switch to non-root user
  USER questiongen
  
  # Expose port for question-generation service
  EXPOSE 8001
  
  # No Docker health check - let Kubernetes handle it
  CMD ["python", "-m", "packages.question_generation_service.main"]