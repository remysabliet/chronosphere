# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## implementation guideline
Aways implement using DRY and SOLID principle
Aways Apply best practices

## Communication Guidelines

Always explain your plan before asking for implementation
Always try to use the minimum possible number of words when explaining stuff to save Token and Money however when it is about implementing code you can use as much as necessary.

## Project Overview

Memosphere is an AI-powered adaptive learning platform built with a microservices architecture. The platform uses BKT (Bayesian Knowledge Tracing) and IRT (Item Response Theory) algorithms to personalize education.

**Package Manager**: pnpm (v10.17.1)
**Monorepo Structure**: pnpm workspaces with packages in `packages/*` and `apps/*`

## Development Commands

### Setup & Running
```bash
# Install dependencies
pnpm install

# Start all services with Docker
pnpm run dev:up

# Stop all services
pnpm run dev:down

# Run individual service in development
cd packages/<service-name>
pnpm run dev
```

### Testing
```bash
# Run all tests (unit + integration)
pnpm run test

# Unit tests only (TypeScript + Python)
pnpm run test:unit

# Integration tests (sets up test DB automatically)
pnpm run test:integration

# E2E tests with Playwright
pnpm run test:e2e

# Watch mode for development
pnpm run test:watch

# Run tests with UI
pnpm run test:ui

# Python service tests (from package root)
cd packages/learning-engine-service && poetry run pytest tests/unit/
cd packages/question-generation-service && poetry run pytest tests/integration/
```

### Linting & Formatting
```bash
# Lint all code
pnpm run lint

# Lint and auto-fix
pnpm run lint:fix

# Format all code
pnpm run format

# Check formatting
pnpm run format:check

# Type checking
pnpm run type-check
```

### Database Migrations
```bash
# Run migrations (from migration-service)
cd packages/migration-service
pnpm run migrate:latest

# Rollback migration
pnpm run migrate:rollback

# Create new migration
pnpm run migrate:make <migration_name>

# Reset database (dev only)
pnpm run db:reset

# Check migration status
pnpm run migrate:status
```

### Building
```bash
# Build all packages
pnpm run build

# Build specific package
cd packages/<service-name>
pnpm run build
```

## Architecture

### Microservices Structure

**TypeScript/Node.js Services:**
- `quiz-session-service` - Real-time quiz orchestration (Port 3003)
- `user-management-service` - Authentication & user profiles (Port 3001)
- `content-management-service` - Learning materials & curriculum
- `analytics-service` - Learning insights & progress tracking
- `notification-service` - Real-time notifications
- `migration-service` - Database migrations with Knex.js

**Python Services (FastAPI):**
- `learning-engine-service` - BKT/IRT algorithms & adaptive decision engine
- `question-generation-service` - AI-powered question creation

**Shared Package:**
- `@memosphere/shared` - Shared types, utilities, and configurations

**Frontend:**
- `apps/web-app` - React frontend application

### Infrastructure

**Docker Compose** (`infrastructure/docker/docker-compose.yml`):
- PostgreSQL 17 (Port 5432)
- Redis 7 (Port 6379)
- All microservices with hot-reload in development
- Environment-based configuration (ENVIRONMENT=development|test)

### Test Organization

```
packages/<service>/tests/
├── unit/           # Unit tests (Vitest for TS, pytest for Python)
└── integration/    # Integration tests (with test DB)
```

- Unit tests: `packages/*/tests/unit/**/*.test.ts`
- Integration tests: `packages/*/tests/integration/**/*.test.ts`
- E2E tests: Playwright (root level)

## Development Patterns

### TypeScript Configuration
- Base config: `tools/configs/tsconfig.base.json`
- Each package extends base config
- ES Modules (`"type": "module"`)

### Python Services
- **Dependency Management**: Poetry
- **Python Version**: 3.13.7
- **Key Libraries**: FastAPI, NumPy, SciPy, scikit-learn, BKT library
- **Formatting**: Black (80 char line length)
- **Import Sorting**: isort (black profile)
- **Type Checking**: mypy (strict mode)

### Git Hooks (Husky)
- **Pre-commit**: Runs `pnpm run lint && pnpm run format`
- **Pre-push**: Runs `pnpm run test:unit`

### Environment Variables
Services expect environment variables for:
- `NODE_ENV` - development/test/production
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- Service-specific vars (JWT_SECRET, PORT, etc.)

## Key Implementation Details

### Database Migrations
- Managed by `migration-service` using Knex.js
- Migrations run automatically in Docker Compose via `migration-service` container
- Test environment creates/destroys isolated test DB
- Migration files: `packages/migration-service/migrations/`

### Testing Strategy
- **Unit tests**: No external dependencies
- **Integration tests**: Automatically spin up PostgreSQL and Redis in Docker (test environment)
- Test DB lifecycle managed by npm scripts (`test:db:create`, `test:db:destroy`)
- Python tests use pytest with async support

### Service Communication
Services are designed for inter-service communication over HTTP/REST (future state), currently most services are stubs.

### Code Quality Tools
- **ESLint**: Flat config format with TypeScript, import ordering
- **Prettier**: 80 char line length, 2 spaces, trailing commas
- **TypeScript**: Strict type checking across all services
- **Python**: Black + isort + mypy for formatting and type safety

