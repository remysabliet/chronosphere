# Notification Service

Multi-channel notifications for reminders, progress updates, and system messages.

## Tech Stack
- **Node.js + Express** (or NestJS)
- **PostgreSQL** + **Redis** for message queuing

## Key Features
- Multi-channel delivery (Email, SMS, Push, In-app)
- Smart scheduling and user preferences
- Template system for notifications
- Delivery tracking and analytics

## API Endpoints
```
POST /notifications/send       # Send notification
POST /notifications/schedule   # Schedule notification
GET  /preferences/:userId      # Get user preferences
PUT  /preferences/:userId      # Update preferences
```

## Development
```bash
pnpm install
cp .env.example .env
PORT=3007 pnpm dev
```

## Local Port: 3007