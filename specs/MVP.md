# 🚀 Memosphere MVP Plan

Memosphere is an AI-powered adaptive learning platform that generates personalized educational questions from text inputs. This MVP focuses on validating the core learning loop: input → question generation → quiz → performance tracking.

---

## 🎯 MVP Objectives

- ✅ Convert text into educational questions
- ✅ Deliver interactive quizzes
- ✅ Track basic user performance
- ✅ Identify weak knowledge areas
- ✅ Lay the foundation for adaptive learning

- Text input for question generation
- Basic question types (MCQ, True/False, Fill-in-the-blanks)
- Simple quiz interface
- User authentication
- Basic performance tracking (score, weak areas)
- PostgreSQL for persistence
- FastAPI for NLP
- Express services for user and analytics
- Nginx as API Gateway
- Next.js frontend with Tailwind UI

---

## 🧱 MVP Architecture Overview

### Frontend
- **Framework**: Next.js 14+ with TypeScript
- **UI**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand
- **Forms**: React Hook Form + Zod
- **Charts**: Recharts (for basic analytics)

### Backend (Microservices)
- **API Gateway**: Nginx (reverse proxy)
- **Question Generation Service**: Python + FastAPI
- **User Management Service**: Node.js + Express
- **Analytics Service**: Node.js + Express
- **Content Management Service**: Node.js + Express

### AI/NLP
- **Primary NLP Engine**: AWS Comprehend
  - Key phrase extraction
  - Custom entity recognition
  - Subject/topic classification

### Database
- **Relational DB**: PostgreSQL
  - Users, sessions, questions, performance
- **Vector DB**: (Optional for MVP) Pinecone or Weaviate
  - Semantic search, similarity matching
- **Cache**: Redis
  - Session management, frequently accessed questions

### Infrastructure
- **Cloud Provider**: AWS
  - ECS/EKS for containers
  - RDS for PostgreSQL
  - S3 for media storage
  - CloudWatch for monitoring

---

## 📦 MVP Feature Array

```ts
const MVP_FEATURES = [
  "User Authentication (Auth0 or AWS Cognito)",
  "Text Input for Question Generation",
  "Basic Question Types (MCQ, True/False, Fill-in-the-blanks)",
  "Simple Quiz Interface",
  "Basic Score Tracking",
  "Weak Area Logging",
  "Session History",
  "Minimal Progress Summary (Chart.js or Recharts)",
  "PostgreSQL for persistence",
  "FastAPI for question generation",
  "Express for user and analytics services",
  "Nginx as API Gateway",
  "Next.js frontend with Tailwind UI"
];
