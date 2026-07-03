# Analytics Service

Computes performance metrics and generates personalized learning insights.

## Tech Stack

- **Node.js + Express** (or NestJS)
- **PostgreSQL** for analytics data

## Key Features

- Session analytics and performance tracking
- Mastery declaration and validation
- Personalized feedback generation
- Learning progress visualization

## API Endpoints

```
POST /analytics/process-session    # Process completed session
GET  /analytics/user/:id           # Get user analytics
POST /mastery/declare              # Declare mastery
GET  /feedback/personalized/:userId # Get personalized feedback
```

## Development

```bash
pnpm install
cp .env.example .env
PORT=3005 pnpm dev
```

## Local Port: 3005

## Testing

```bash
# Run tests with coverage (requires ≥80% line coverage)
pnpm test:coverage

# Run tests in watch mode
pnpm test
```

Tests live in `tests/unit/`. Coverage is measured on `src/**/*.ts` using vitest + @vitest/coverage-v8.
