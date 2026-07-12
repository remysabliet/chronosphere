# 🚀 Memosphere MVP Development Plan

## 📋 Project Overview

**Memosphere** is an AI-powered adaptive learning platform that generates personalized educational questions using BKT (Bayesian Knowledge Tracing) and IRT (Item Response Theory) models. The MVP includes:

- **Frontend**: Next.js 14+ with TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Microservices architecture (Node.js + Python FastAPI)
- **Database**: PostgreSQL with Redis caching
- **AI**: Mistral Large API for question generation
- **Infrastructure**: Kubernetes on AWS EC2 with CI/CD pipeline

---

## 🎯 MVP Objectives

**Legend:** ✅ done · 🟡 partial · ⬜ not started — see [Implementation Status](#-implementation-status-as-of-2026-07-09) below for detail.

- ✅ Convert text into educational questions using AI
- ✅ Deliver adaptive, personalized quiz experiences
- 🟡 Track user performance with BKT and IRT models — BKT is live; IRT hasn't been started
- 🟡 Identify weak knowledge areas and learning gaps — mastery is tracked per concept-Bloom pair; nothing surfaces it in a UI yet
- ⬜ Implement spaced repetition for long-term retention — not started
- 🟡 Provide real-time feedback and progress visualization — in-session feedback works; no analytics dashboard
- ⬜ Support multiple user roles and access levels — single implicit learner role only, no Admin/Moderator flows
- ⬜ Enable user feedback for continuous improvement — no rating/flagging UI

---

## 📍 Implementation Status (as of 2026-07-09)

**One service is real; the rest are scaffolds.** `question-generation-service` (Python/FastAPI) has absorbed nearly the entire backend — thema extraction, quiz creation, question generation, quiz-taking, and the adaptive/BKT engine all live there. `user-management-service`, `content-management-service`, `quiz-session-service`, `analytics-service`, and `notification-service` are unstarted: each is a single `index.ts` that answers `/health` via plain Node `http` — not NestJS or Express, despite the tech stack listed below. `learning-engine-service` is a matching FastAPI stub ("BKT and IRT — Coming Soon"). See [docs/diagram/architecture.md](../diagram/architecture.md) for the full topology, including which edges are real traffic vs. configured-but-unused.

### Core adaptive loop (main-workflow.md steps)

| Step | Covers                                                    | Status                                                                                                                     |
| ---- | --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 1-3  | Thema/topic extraction, exposure capture, placement probe | ✅ Done — `thema_router`, `wizard_router`, `exposure_service`                                                              |
| 4    | Quiz session initialization                               | ✅ Done — `POST /v1/quizzes`, outbox-driven                                                                                |
| 5-6  | Exposure → P(L0), concept-Bloom mapping                   | ✅ Done — `ConceptService`, `EXPOSURE_TO_P_L0`                                                                             |
| 7    | BKT initialization                                        | ✅ Done — `BktInitService`, seeds `concept_progress_tracker`                                                               |
| 8    | Question generation & pooling                             | ✅ Done — outbox relay + `GenerationWorker`, batched Mistral pipeline, plus a live-LLM fallback when a bucket is exhausted |
| 8A   | Question validation (structural + LLM judge)              | ✅ Done — `question_validation_service`, Prompt 4 judge                                                                    |
| 9    | Response logging                                          | ✅ Done — `user_responses`                                                                                                 |
| 10   | BKT model update                                          | ✅ Done — `MasteryService.record_attempt`                                                                                  |
| 11   | Adaptive decision engine (Remediate/Practice/Advance)     | ✅ Done — `AdaptiveSelectionService`, Bloom-ladder climbing, live-LLM fallback                                             |
| A-E  | Spaced repetition / FSRS review scheduling                | ⬜ Not started — `mastery_log`, `fsrs_state`, `review_queue` tables exist in migrations; no application code touches them  |
| —    | IRT (Item Response Theory)                                | ⬜ Not started — referenced only in a stub docstring, no implementation                                                    |

### Frontend

- ✅ Auth (NextAuth + Cognito), quiz-creation chat wizard, quiz library, quiz detail with live progress polling, session runner (answer → feedback → next question) — all wired to the real API.
- ⬜ Profile, Analytics, and Memocards pages exist as routes but render "Coming Soon" — no UI behind them.
- ⬜ Manual quiz creation (`/quiz/new/manual`) is a stub; the chat wizard is the only working creation path.

### Infrastructure

- ✅ Local dev: `docker-compose` (Postgres, Redis, nginx, all 9 services) — real and runnable.
- 🟡 nginx gateway is correctly configured for all 7 backend services, but the only real traffic (web-app → question-generation-service) bypasses it entirely.
- ⬜ AWS target infra (EC2 Kubernetes, RDS, ElastiCache, ECR, self-hosted CI runner) — no Terraform/IaC or k8s manifests exist. CI (`ci.yml`) currently only lints/type-checks/tests on GitHub-hosted runners.

### Known gaps worth calling out

- No rate limiting on the live-LLM fallback inside session-taking (only the direct `/v1/questions/generate` endpoint is rate-limited today).
- No RBAC/roles beyond a single implicit learner role.
- No question rating/flagging UI; `moderation_router` is an empty `APIRouter` with no endpoints registered.

---

## 🏗️ MVP Architecture Overview

### Frontend

- **Framework**: Next.js 14+ with TypeScript
- **UI**: Tailwind CSS + shadcn/ui / Radix
- **State Management**: Zustand
- **Forms**: React Hook Form + Zod
- **Charts**: Recharts (for basic analytics)

### Backend (Microservices)

- **API Gateway**: Nginx (reverse proxy) — ✅ running, configured for all services, but bypassed by the only real traffic path (see Implementation Status)
- **Question Generation Service**: Python + FastAPI — ✅ the only fully implemented backend; owns thema/quiz/question/session/BKT/adaptive logic
- **Learning Engine Service**: Python + FastAPI — ⬜ health-check stub only
- **Quiz Session Service**: originally planned as Node.js — ⬜ health-check stub only (its intended scope now lives in Question Generation Service)
- **User Management Service**: originally planned as Node.js — ⬜ health-check stub only (plain `http`, not Express/NestJS)
- **Analytics Service**: originally planned as Node.js — ⬜ health-check stub only (plain `http`, not Express/NestJS)
- **Content Management Service**: originally planned as Node.js — ⬜ health-check stub only (plain `http`, not Express/NestJS)
- **Notification Service**: originally planned as Node.js — ⬜ health-check stub only (plain `http`, not Express/NestJS)

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
  - **Database**: Amazon RDS PostgreSQL (Free Tier: 750 hrs/year)
  - **Authentication**: Amazon Cognito (Free Tier: 50,000 MAUs)
  - **Storage**: Amazon S3 (Free Tier: 5GB)
  - **Caching**: Amazon ElastiCache Redis (Optional for MVP)
  - **API Gateway**: NGINX on Kubernetes on EC2
  - **CI/CD**: GitHub Actions + Amazon ECR (Self-hosted runners)
  - **Monitoring**: Amazon CloudWatch

---

## 📦 MVP Feature Array

Status tags below: ✅ done · 🟡 partial · ⬜ not started (see [Implementation Status](#-implementation-status-as-of-2026-07-09)).

```ts
const MVP_FEATURES = [
  // User Management
  'User Registration & Login (OAuth2 Social Login)', // ✅ Cognito + NextAuth
  'User Profile Creation (Age, Profession, Education)', // ⬜ Profile page is a stub
  'Role-Based Access Control (Learner, Admin, Moderator)', // ⬜ single implicit learner role only

  // Content Input & Processing
  'Text Input for Question Generation', // ✅ thema/wizard flow
  'AI-Powered Question Generation from Text', // ✅ Mistral pipeline, async + live fallback
  'Question Validation & Quality Control', // ✅ structural checks + LLM judge

  // Learning Experience
  'Interactive Quiz Sessions', // ✅ start/answer/summary all live
  'Multiple Question Types (MCQ, True/False, Fill-in-the-blanks)', // ✅ MCQ/MCQMultiSelect/TrueFalse/FillInBlank
  'Adaptive Question Selection', // ✅ Step 11 Remediate/Practice/Advance engine
  'Real-time Performance Feedback', // ✅ correctness + explanation after every answer

  // Progress Tracking
  'Session History & Analytics', // ⬜ Analytics page is a stub
  'Performance Metrics (Score, Response Time)', // 🟡 captured in user_responses/SessionSummary; no metrics UI
  'Weak Area Identification', // ⬜ concept_progress_tracker data exists; nothing surfaces it
  'Learning Progress Visualization', // ⬜ Analytics page is a stub

  // Spaced Repetition
  'Memory Refresh Module', // ⬜ not started
  'Review Queue Management', // ⬜ review_queue table exists, unused
  'Mastery Tracking per Concept', // ✅ concept_progress_tracker + BKT update

  // User Feedback
  'Question Rating System (1-5 stars)', // ⬜ not started
  'Question Flagging (Confusing, Incorrect, etc.)', // ⬜ moderation_router has no endpoints yet
  'Session Completion Feedback', // 🟡 SessionSummary API exists; completion UI not verified rich
];
```

---

## 🗓️ Development Phases & Time Estimates

> **Note:** this phase breakdown and its hour estimates are the original pre-build plan and haven't been re-scoped against actual progress. In practice, most of Phase 2.1-2.2's AI integration and learning-algorithm work (question generation, validation, BKT, adaptive selection) is already done, folded entirely into Question Generation Service rather than split across separate services as planned. See [Implementation Status](#-implementation-status-as-of-2026-07-09) above for what's actually built.

### **Phase 1: Project Foundation & Local Development Setup**

**Duration: 2-3 weeks (80-120 hours)**

#### 1.1 Development Environment Setup (16-24 hours)

- **Local Development Stack** (8-12 hours)
  - Set up monorepo structure with pnpm workspaces
  - Configure TypeScript, ESLint, Prettier
  - Set up Docker for local development
  - Configure VS Code workspace settings

- **Database Setup** (8-12 hours)
  - Install and configure PostgreSQL locally
  - Set up Redis for caching
  - Create database migration system
  - Implement database seeding scripts

#### 1.2 Core Infrastructure Setup (24-36 hours)

- **Database Schema Implementation** (16-24 hours)
  - Create all tables from `db-schema.md`
  - Implement foreign key constraints and indexes
  - Set up database migrations with proper versioning
  - Create seed data for default roles and configuration

- **Authentication System** (8-12 hours)
  - Set up Amazon Cognito integration
  - Implement OAuth2 social login (Google, Apple, Facebook)
  - Create JWT token handling middleware
  - Implement role-based access control (RBAC)

#### 1.3 Basic API Structure (24-36 hours)

- **Microservices Foundation** (16-24 hours)
  - Set up User Management Service (Node.js + Express)
  - Set up Learning Engine Service (Python + FastAPI)
  - Set up Quiz Session Service (Node.js + Express)
  - Set up Question Generation Service (Python + FastAPI)
  - Set up Analytics Service (Node.js + Express)

- **API Gateway Setup** (8-12 hours)
  - Configure NGINX as reverse proxy
  - Set up service discovery and load balancing
  - Implement request routing and middleware

#### 1.4 Frontend Foundation (16-24 hours)

- **Next.js Application Setup** (8-12 hours)
  - Initialize Next.js 14+ with TypeScript
  - Configure Tailwind CSS and shadcn/ui components
  - Set up state management with Zustand
  - Configure React Hook Form + Zod validation

- **Basic UI Components** (8-12 hours)
  - Create authentication pages (login, register)
  - Build user profile setup forms
  - Implement basic dashboard layout
  - Set up routing and navigation

---

### **Phase 2: Core Learning Engine Development**

**Duration: 3-4 weeks (120-160 hours)**

#### 2.1 AI Integration & Question Generation (40-56 hours)

- **Mistral API Integration** (16-24 hours)
  - Set up Mistral Large API client
  - Implement API rate limiting and error handling
  - Create prompt templates for all 3 phases
  - Build question generation pipeline

- **Question Validation System** (16-24 hours)
  - Implement `validate_question()` function from `python-functions.md`
  - Create quality scoring algorithms
  - Build validation logging system
  - Implement question feedback collection

- **Content Processing Pipeline** (8-12 hours)
  - Implement Thema extraction (Prompt 1)
  - Build concept mapping system (Prompt 2)
  - Create question generation logic (Prompt 3)
  - Set up content moderation tools

#### 2.2 Learning Algorithms Implementation (40-56 hours)

- **BKT Algorithm Implementation** (16-24 hours)
  - Implement `update_bkt()` function from `python-functions.md`
  - Create mastery tracking system
  - Implement mastery declaration logic

- **FSRS Scheduling & Difficulty Calibration** (8-16 hours)
  - Integrate `py-fsrs` library (review scheduling + predicted recall as the decay signal)
  - Build the generator-calibration check (LLM tier labels vs. observed correct rates per concept–tier)
  - Implement adaptive question selection (decision bands + tier matching)

- **Adaptive Decision Engine** (8-12 hours)
  - Create decision logic for question selection
  - Implement reinforcement, advancement, and remediation logic
  - Build Bloom level progression tracking
  - Create spaced repetition scheduling

#### 2.3 Quiz Session Management (24-32 hours)

- **Session Lifecycle** (12-16 hours)
  - Implement session initialization
  - Create question delivery system
  - Build response collection and validation
  - Implement session completion logic

- **Progress Tracking** (12-16 hours)
  - Create performance metrics calculation
  - Implement confidence tracking
  - Build learning progression visualization
  - Create session analytics

#### 2.4 User Experience Features (16-24 hours)

- **Interactive Quiz Interface** (8-12 hours)
  - Build question display components
  - Create answer selection interface
  - Implement timer and progress indicators
  - Add hint system for struggling learners

- **Feedback & Rating System** (8-12 hours)
  - Create question rating interface
  - Implement flagging system for problematic questions
  - Build feedback collection forms
  - Create user feedback analytics

---

### **Phase 3: Advanced Features & Analytics**

**Duration: 2-3 weeks (80-120 hours)**

#### 3.1 Analytics & Reporting (32-48 hours)

- **Performance Analytics** (16-24 hours)
  - Implement session analytics dashboard
  - Create mastery progression tracking
  - Build weak area identification
  - Create learning path recommendations

- **Admin & Moderator Tools** (16-24 hours)
  - Build content moderation interface
  - Create question quality monitoring
  - Implement user management tools
  - Build system health monitoring

#### 3.2 Advanced Learning Features (24-36 hours)

- **Spaced Repetition System** (12-18 hours)
  - Implement review queue management
  - Create decay threshold calculations
  - Build reinforcement scheduling
  - Create memory refresh modules

- **Personalization Engine** (12-18 hours)
  - Implement user preference learning
  - Create adaptive difficulty adjustment
  - Build learning style adaptation
  - Create personalized recommendations

#### 3.3 Data Management & Optimization (24-36 hours)

- **Caching Strategy** (8-12 hours)
  - Implement Redis caching for frequently accessed data
  - Create cache invalidation strategies
  - Build performance optimization
  - Implement data preloading

- **Data Export & Backup** (8-12 hours)
  - Create data export functionality
  - Implement backup strategies
  - Build data migration tools
  - Create analytics data export

- **Performance Optimization** (8-12 hours)
  - Implement database query optimization
  - Create API response caching
  - Build frontend performance optimization
  - Implement lazy loading and code splitting

---

### **Phase 4: Testing & Quality Assurance**

**Duration: 2-3 weeks (80-120 hours)**

#### 4.1 Testing Implementation (40-56 hours)

- **Unit Testing** (16-24 hours)
  - Write tests for all Python functions
  - Create Node.js service tests
  - Implement frontend component tests
  - Build API endpoint tests

- **Integration Testing** (16-24 hours)
  - Create end-to-end workflow tests
  - Implement microservice integration tests
  - Build database integration tests
  - Create AI service integration tests

- **Performance Testing** (8-12 hours)
  - Implement load testing for APIs
  - Create database performance tests
  - Build frontend performance tests
  - Test AI service response times

#### 4.2 Security & Compliance (24-32 hours)

- **Security Implementation** (16-24 hours)
  - Implement input validation and sanitization
  - Create SQL injection prevention
  - Build XSS protection
  - Implement rate limiting and DDoS protection

- **Data Privacy & Compliance** (8-12 hours)
  - Implement GDPR compliance features
  - Create data anonymization tools
  - Build consent management
  - Create data retention policies

#### 4.3 Bug Fixing & Optimization (16-24 hours)

- **Bug Resolution** (8-12 hours)
  - Fix identified bugs and issues
  - Optimize performance bottlenecks
  - Resolve integration problems
  - Fix UI/UX issues

- **Code Quality** (8-12 hours)
  - Implement code review processes
  - Create documentation
  - Optimize code structure
  - Implement monitoring and logging

---

### **Phase 5: Cloud Infrastructure & Deployment**

**Duration: 2-3 weeks (80-120 hours)**

#### 5.1 AWS Infrastructure Setup (32-48 hours)

- **EC2 & Kubernetes Setup** (16-24 hours)
  - Set up EC2 instances for Kubernetes cluster
  - Install and configure Kubernetes
  - Set up cluster networking and security
  - Configure persistent storage

- **Database & Storage Setup** (16-24 hours)
  - Set up Amazon RDS PostgreSQL
  - Configure Amazon S3 for file storage
  - Set up Amazon ElastiCache Redis
  - Implement backup and recovery

#### 5.2 CI/CD Pipeline Implementation (24-32 hours)

- **GitHub Actions Setup** (12-16 hours)
  - Configure self-hosted GitHub runners on EC2
  - Set up automated testing workflows
  - Create Docker image building and pushing
  - Implement deployment automation

- **Container Registry & Deployment** (12-16 hours)
  - Set up Amazon ECR for container storage
  - Configure Kubernetes deployment manifests
  - Implement rolling update strategies
  - Set up monitoring and health checks

#### 5.3 Production Configuration (24-40 hours)

- **Security & Monitoring** (12-20 hours)
  - Configure SSL/TLS certificates
  - Set up CloudWatch monitoring
  - Implement log aggregation
  - Create alerting and notification systems

- **Performance & Scalability** (12-20 hours)
  - Configure auto-scaling policies
  - Set up load balancing
  - Implement caching strategies
  - Create performance monitoring

---

### **Phase 6: Launch Preparation & Documentation**

**Duration: 1-2 weeks (40-80 hours)**

#### 6.1 Documentation & Training (16-24 hours)

- **Technical Documentation** (8-12 hours)
  - Create API documentation
  - Write deployment guides
  - Create troubleshooting guides
  - Document configuration options

- **User Documentation** (8-12 hours)
  - Create user guides and tutorials
  - Build help system
  - Create video tutorials
  - Write FAQ and support documentation

#### 6.2 Launch Preparation (24-32 hours)

- **Pre-launch Testing** (12-16 hours)
  - Conduct final testing and validation
  - Perform security audits
  - Test backup and recovery procedures
  - Validate all integrations

- **Launch Activities** (12-16 hours)
  - Set up production monitoring
  - Create launch checklist
  - Prepare rollback procedures
  - Set up user onboarding

#### 6.3 Post-Launch Support (16-24 hours)

- **Monitoring & Maintenance** (8-12 hours)
  - Set up production monitoring
  - Create maintenance procedures
  - Implement update processes
  - Create support procedures

- **Performance Optimization** (8-12 hours)
  - Monitor system performance
  - Optimize based on real usage
  - Implement improvements
  - Scale resources as needed

---

## 📊 Total Time Estimate Summary

| Phase                          | Duration        | Hours        | Key Deliverables                                       |
| ------------------------------ | --------------- | ------------ | ------------------------------------------------------ |
| **Phase 1: Foundation**        | 2-3 weeks       | 80-120h      | Local dev environment, basic APIs, frontend foundation |
| **Phase 2: Core Engine**       | 3-4 weeks       | 120-160h     | AI integration, learning algorithms, quiz system       |
| **Phase 3: Advanced Features** | 2-3 weeks       | 80-120h      | Analytics, personalization, optimization               |
| **Phase 4: Testing & QA**      | 2-3 weeks       | 80-120h      | Comprehensive testing, security, bug fixes             |
| **Phase 5: Cloud Deployment**  | 2-3 weeks       | 80-120h      | AWS infrastructure, CI/CD, production setup            |
| **Phase 6: Launch Prep**       | 1-2 weeks       | 40-80h       | Documentation, final testing, launch                   |
| **TOTAL**                      | **12-18 weeks** | **480-720h** | **Complete MVP with production deployment**            |

---

## 🎯 Recommended Team Structure

### **Solo Developer Approach** (480-720 hours)

- **Full-stack developer** with experience in:
  - Node.js/TypeScript
  - Python/FastAPI
  - React/Next.js
  - PostgreSQL
  - AWS/Kubernetes
  - AI/ML integration

### **Small Team Approach** (3-4 developers, 12-15 weeks)

- **Backend Developer** (Python/Node.js): 200-250 hours
- **Frontend Developer** (React/Next.js): 150-200 hours
- **DevOps Engineer** (AWS/Kubernetes): 100-150 hours
- **AI/ML Engineer** (Mistral API integration): 80-120 hours

---

## 🚀 Critical Success Factors

1. **Start with Phase 1** - Solid foundation is crucial
2. **Implement testing early** - Don't wait until Phase 4
3. **Use AWS Free Tier** - Minimize costs during development
4. **Focus on core learning loop** - Question generation → Quiz → Analytics
5. **Iterate quickly** - Build MVP features first, enhance later
6. **Monitor performance** - Set up logging and monitoring from day one

---

## 🔧 Development Principles

### SOLID Principles

- **Single Responsibility**: Each microservice has one clear purpose
- **Open/Closed**: Services are open for extension, closed for modification
- **Liskov Substitution**: Services can be replaced without breaking functionality
- **Interface Segregation**: Clean, focused API interfaces
- **Dependency Inversion**: Depend on abstractions, not concretions

### DRY Principles

- **Reusable Components**: Shared UI components and utilities
- **Common Libraries**: Shared business logic across services
- **Template System**: Reusable prompt templates for AI
- **Configuration Management**: Centralized configuration for all services

### Best Practices

- **Clear Naming**: Descriptive function and variable names
- **Consistent Formatting**: Standardized code style across all languages
- **Logical Modularization**: Well-structured, maintainable code
- **JSDoc Comments**: Comprehensive documentation for complex functions
- **Inline Comments**: Clear explanations for complex logic

---

## 📈 Success Metrics

### Technical Metrics

- **API Response Time**: < 200ms for question generation
- **Database Performance**: < 100ms for user queries
- **Frontend Load Time**: < 3 seconds initial load
- **Uptime**: 99.9% availability
- **Error Rate**: < 0.1% for critical operations

### Business Metrics

- **User Engagement**: Average session duration > 15 minutes
- **Learning Effectiveness**: 80%+ correct answers on mastered concepts
- **User Satisfaction**: 4.5+ stars average rating
- **Retention**: 70%+ weekly active users
- **Question Quality**: 90%+ questions pass validation

---

## 🎯 Next Steps

1. **Review and approve this plan** with stakeholders
2. **Set up development environment** (Phase 1.1)
3. **Create project repository** with proper structure
4. **Begin database schema implementation** (Phase 1.2)
5. **Start with User Management Service** (Phase 1.3)

This comprehensive plan provides a clear roadmap from local development to production deployment, ensuring a successful MVP launch within 12-18 weeks.
