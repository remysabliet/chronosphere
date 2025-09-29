# =============================================================================
# Ultra-Optimized Multi-Stage Dockerfile for Learning Engine Service
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
  
  # Install system dependencies for ML libraries
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
  
  # Set working directory
  WORKDIR /app
  
  # Copy Poetry configuration
  COPY packages/learning-engine-service/pyproject.toml ./packages/learning-engine-service/
  COPY packages/learning-engine-service/poetry.lock* ./packages/learning-engine-service/
  
  # Install Poetry
  RUN pip install poetry==1.7.1
  
  # Configure Poetry
  ENV POETRY_NO_INTERACTION=1 \
      POETRY_VENV_IN_PROJECT=1 \
      POETRY_CACHE_DIR=/tmp/poetry_cache
  
  # Install dependencies
  WORKDIR /app/packages/learning-engine-service
  RUN poetry install --only=main && poetry cache clear --all .
  
  # -----------------------------------------------------------------------------
  # Stage 2: Build - Application setup
  # -----------------------------------------------------------------------------
  FROM base AS build
  
  # Copy application source code
  COPY packages/learning-engine-service/ ./packages/learning-engine-service/
  
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
      libblas3 \
      liblapack3 \
      libatlas3-base \
      gfortran \
      && rm -rf /var/lib/apt/lists/* \
      && apt-get clean
  
  # Create non-root user for security
  RUN groupadd --gid 1001 python && \
      useradd --uid 1001 --gid python --shell /bin/bash --create-home learningengine
  
  # Set working directory
  WORKDIR /app
  
  # Copy requirements and install Python dependencies
  COPY --from=build /app/packages/learning-engine-service/requirements.txt ./requirements.txt
  RUN pip install --no-cache-dir --user -r requirements.txt
  
  # Copy application code
  COPY --from=build --chown=learningengine:python /app/packages/learning-engine-service ./packages/learning-engine-service
  
  # Switch to non-root user
  USER learningengine
  
  # Expose port for learning-engine service
  EXPOSE 8002
  
  # No Docker health check - let Kubernetes handle it
  CMD ["python", "-m", "packages.learning_engine_service.main"]