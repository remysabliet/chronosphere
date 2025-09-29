# Content Management Service

Content moderation and quality control tools for moderators and admins.

## Tech Stack
- **Node.js + Express** (or NestJS)
- **PostgreSQL** + **AWS S3** for file storage

## Key Features
- Content moderation and review
- Question quality assessment
- Learning unit management
- Admin dashboard and reporting

## API Endpoints
```
GET  /moderation/queue          # Get pending moderation items
POST /moderation/review         # Submit moderation decision
GET  /questions/flagged         # Get flagged questions
PUT  /questions/:id/approve     # Approve question
```

## Development
```bash
pnpm install
cp .env.example .env
PORT=3006 pnpm dev
```

## Local Port: 3006