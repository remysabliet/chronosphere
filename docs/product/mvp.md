# 🚀 Memosphere MVP Plan

Memosphere is an AI-powered adaptive learning platform that generates personalized educational questions from text inputs. This MVP focuses on validating the core learning loop: input → question generation → quiz → performance tracking.

---

## 🎯 MVP Objectives

**Legend:** ✅ done · 🟡 partial · ⬜ not started — full detail and per-step breakdown in [mvp-planning.md § Implementation Status](mvp-planning.md#-implementation-status-as-of-2026-07-09).

- ✅ Convert text into educational questions using AI
- ✅ Deliver adaptive, personalized quiz experiences
- 🟡 Track user performance with BKT and IRT models — BKT is live; IRT hasn't been started
- 🟡 Identify weak knowledge areas and learning gaps — mastery is tracked; no reporting UI yet
- ⬜ Implement spaced repetition for long-term retention — not started
- 🟡 Provide real-time feedback and progress visualization — in-session feedback works; no analytics dashboard
- ⬜ Support multiple user roles and access levels — single implicit learner role only
- ⬜ Enable user feedback for continuous improvement — no rating/flagging UI

**Only `question-generation-service` (Python/FastAPI) is actually built.** It has absorbed thema extraction, quiz creation, question generation, quiz-taking, and the adaptive/BKT engine. Every other backend service listed below is a health-check-only scaffold.

---

## 🧱 MVP Architecture Overview

### Frontend

- **Framework**: Next.js 14+ with TypeScript
- **UI**: Tailwind CSS + shadcn/ui / Radix
- **State Management**: Zustand
- **Forms**: React Hook Form + Zod
- **Charts**: Recharts (for basic analytics)

### Backend (Microservices)

- **API Gateway**: Nginx (reverse proxy) — ✅ running, but bypassed by the only real traffic path
- **Question Generation Service**: Python + FastAPI — ✅ the only fully implemented backend
- **Learning Engine Service**: Python + FastAPI — ⬜ health-check stub only
- **User Management Service**, **Analytics Service**, **Content Management Service**, **Notification Service**, **Quiz Session Service**: originally planned as Node.js — ⬜ all health-check stubs only (plain `http`, not Express/NestJS)

### AI/NLP

- **Primary LLM**: Mistral Large API
  - Question generation from text inputs
  - Content summarization and analysis
  - Adaptive learning recommendations
  - Text preprocessing (key phrases, entities, syntax analysis)

### Database

- **Relational DB**: PostgreSQL
  - Users, sessions, questions, performance
- **Vector DB**: (Optional for MVP) Pinecone or Weaviate
  - Semantic search, similarity matching
- **Cache**: Redis
  - Session management, frequently accessed questions

### Infrastructure

- **Cloud Provider**: AWS
  - **Compute**: Kubernetes on EC2 (Manual scaling, cost-effective)
  - **Database**: Amazon RDS PostgreSQL (Free Tier: 750 hrs/month)
  - **Authentication**: Amazon Cognito (Free Tier: 50,000 MAUs)
  - **Storage**: Amazon S3 (Free Tier: 5GB)
  - **Caching**: Amazon ElastiCache Redis (Optional for MVP)
  - **API Gateway**: NGINX on Kubernetes on EC2
  - **CI/CD**: GitHub Actions + Amazon ECR (Self-hosted runners)
  - **Monitoring**: Amazon CloudWatch

---

## 📦 MVP Feature Array

Per-feature status is tracked in [mvp-planning.md](mvp-planning.md#-mvp-feature-array) — this list is kept unannotated here to avoid two copies drifting out of sync.

```ts
const MVP_FEATURES = [
  // User Management
  'User Registration & Login (OAuth2 Social Login)',
  'User Profile Creation (Age, Profession, Education)',
  'Role-Based Access Control (Learner, Admin, Moderator)',

  // Content Input & Processing
  'Text Input for Question Generation',
  'AI-Powered Question Generation from Text',
  'Question Validation & Quality Control',

  // Learning Experience
  'Interactive Quiz Sessions',
  'Multiple Question Types (MCQ, True/False, Fill-in-the-blanks)',
  'Adaptive Question Selection',
  'Real-time Performance Feedback',

  // Progress Tracking
  'Session History & Analytics',
  'Performance Metrics (Score, Response Time)',
  'Weak Area Identification',
  'Learning Progress Visualization',

  // Spaced Repetition
  'Memory Refresh Module',
  'Review Queue Management',
  'Mastery Tracking per Concept',

  // User Feedback
  'Question Rating System (1-5 stars)',
  'Question Flagging (Confusing, Incorrect, etc.)',
  'Session Completion Feedback',
];
```
