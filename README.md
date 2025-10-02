# Memosphere 🧠

> AI-powered adaptive learning platform that personalizes education for every learner.

## 🚀 Quick Start

```bash
# Install dependencies
pnpm install

# Start development environment
pnpm run dev:up

# Run tests
pnpm run test
```

## 🏗️ Architecture

**Microservices Architecture** with TypeScript/Node.js and Python services:

- **🎯 Quiz Session Service** - Real-time quiz orchestration
- **👤 User Management** - Authentication & user profiles
- **📚 Content Management** - Learning materials & curriculum
- **📊 Analytics Service** - Learning insights & progress tracking
- **🔔 Notification Service** - Real-time notifications
- **🤖 Question Generation** - AI-powered question creation (Python)
- **🧠 Learning Engine** - Adaptive learning algorithms (Python)

## 🛠️ Tech Stack

- **Frontend**: React, TypeScript
- **Backend**: Node.js, Express, TypeScript
- **AI/ML**: Python, Poetry
- **Database**: PostgreSQL, Redis
- **Infrastructure**: Docker, Docker Compose, NGINX
- **Testing**: Vitest, Playwright, pytest
- **CI/CD**: GitHub Actions, Husky

## 📁 Project Structure

```
memosphere/
├── apps/web-app/                 # Frontend application
├── packages/                     # Microservices
│   ├── analytics-service/        # Learning analytics
│   ├── content-management/       # Content & curriculum
│   ├── learning-engine/          # AI learning algorithms (Python)
│   ├── notification-service/     # Real-time notifications
│   ├── question-generation/      # AI question creation (Python)
│   ├── quiz-session-service/     # Quiz orchestration
│   └── user-management/          # User auth & profiles
├── infrastructure/               # Docker & NGINX config
└── docs/                        # Documentation
```

## 🧪 Testing

```bash
# Run all tests
pnpm run test

# Unit tests only
pnpm run test:unit

# Integration tests
pnpm run test:integration

# E2E tests
pnpm run test:e2e

# Watch mode for development
pnpm run test:watch
```

## 🚀 Development

```bash
# Start all services
pnpm run dev:up

# Stop services
pnpm run dev:down

# Lint & format
pnpm run lint
pnpm run format
```

## 🔧 Pre-commit Hooks

Automated quality checks with Husky:

- **Pre-commit**: Runs linting & formatting (`pnpm run lint:fix && pnpm run format`)
- **Pre-push**: Runs unit & integration tests (`pnpm run test:unit`)

## 📚 Documentation

- [Architecture Overview](docs/infra-architecture.md)
- [Database Schema](docs/db-schema.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)

## 📄 License

ISC License - see [LICENSE](LICENSE) for details.

---

**Built with ❤️ for personalized learning**# Test pre-commit hook
