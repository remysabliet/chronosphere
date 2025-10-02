# User Management Service

Handles authentication, user profiles, roles, and permissions for Memosphere.

## Tech Stack

- **Node.js + Express** (or NestJS)
- **PostgreSQL** + **JWT** + **Amazon Cognito**

## Key Features

- OAuth2 social login (Google, Apple, Facebook)
- Role-based access control (learner, admin, moderator, content_creator, analyst)
- User profile management
- Permission validation

## API Endpoints

```
POST /auth/login          # User login
POST /auth/register       # User registration
GET  /users/profile       # Get user profile
PUT  /users/profile       # Update user profile
GET  /users/:id/permissions # Get user permissions
```

## Development

```bash
pnpm install
cp .env.example .env
PORT=3001 pnpm dev
```

## Local Port: 3001
