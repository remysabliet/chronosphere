# Quiz Session Service

Orchestrates quiz sessions, question delivery, and response collection.

## Tech Stack

- **Node.js + Express** (or NestJS)
- **PostgreSQL** + **WebSocket** for real-time features

## Key Features

- Session lifecycle management
- Real-time question delivery
- Response processing and validation
- Progress tracking and statistics

## API Endpoints

```
POST /sessions              # Create quiz session
GET  /sessions/:id/question # Get current question
POST /sessions/:id/response # Submit response
GET  /sessions/:id/progress # Get session progress
```

## Development

```bash
pnpm install
cp .env.example .env
PORT=3003 pnpm dev
```

## Local Port: 3003
