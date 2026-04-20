# Memosphere Web Application

> AI-powered adaptive learning platform with multimedia quizzes, spaced repetition, and interactive memocards.

---

## 🛠️ Tech Stack

### Core

- **Next.js 16** - React 19 framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling

### UI & Components

- **shadcn/ui + Radix UI** - Accessible component primitives
- **Lucide React** - Icon system
- **Framer Motion** - Animations (card flips, transitions, gestures)
- **@dnd-kit** - Drag-and-drop (matching/ordering questions)

### State & Data

- **TanStack Query v5** - Server state, API caching (replaces axios + SWR)
- **Zustand** - Client state (quiz session, user prefs)
- **React Hook Form + Zod** - Forms and validation

### Multimedia

- **Howler.js** - Audio engine (TTS, listening comprehension, sound effects)
- **next/image** - Optimized images

### Other

- **Recharts** - Analytics charts
- **Auth.js (NextAuth.js v5)** - Authentication (AWS Cognito)
- **Socket.io Client** - Real-time quiz sessions
- **date-fns** - Date utilities (spaced repetition scheduling)

---

## 🚫 Libraries We're NOT Using (Overlaps Eliminated)

| ❌ Avoided              | ✅ Using Instead       | Reason                                           |
| ----------------------- | ---------------------- | ------------------------------------------------ |
| **Axios**               | TanStack Query + fetch | Query handles caching/retries; fetch is built-in |
| **SWR**                 | TanStack Query v5      | More features (mutations, devtools)              |
| **Redux**               | Zustand                | 90% less code, 1KB vs 11KB                       |
| **React Spring/GSAP**   | Framer Motion          | One library for all animations                   |
| **react-beautiful-dnd** | @dnd-kit               | Deprecated by Atlassian                          |
| **Chart.js**            | Recharts               | React-native, composable                         |
| **Material-UI/Chakra**  | shadcn/ui              | No 300KB bundle, full control                    |
| **react-icons**         | lucide-react           | Tree-shakable, 17MB → <1MB                       |
| **Formik**              | React Hook Form        | 3x faster, better TypeScript                     |
| **moment.js**           | date-fns               | Deprecated, 67KB → 16KB                          |
| **use-sound**           | Howler.js              | More features, direct Web Audio API              |
| **react-card-flip**     | Framer Motion          | Framer handles all animations                    |
| **Auth0/Clerk**         | Auth.js                | Free, open-source                                |

---

Visual Identity:
🧠 Brain/Learning theme - Purple/blue gradients (intelligence, growth)
✨ Modern & Clean - Glassmorphism, subtle animations
🎯 Conversion-focused - Clear CTAs, social proof
♿ Accessible - WCAG 2.1 AA compliant, semantic HTML

---

## 🏗️ Architecture Philosophy

### Hybrid: Feature-First + Clean Architecture Principles

We adopt a **pragmatic approach** inspired by [Lazar Nikolov's Next.js Clean Architecture](https://github.com/nikolovlazar/nextjs-clean-architecture), balancing maintainability with development velocity:

#### Why This Hybrid?

1. **Feature isolation** - Each domain (quiz, memocard, analytics) is self-contained
2. **Clean Architecture within features** - Business logic separated from UI/infrastructure
3. **Not over-engineered** - No global CA hierarchy for simple features
4. **Scalable** - Add new features without touching existing ones

#### When to Use Full Clean Architecture?

- ✅ **Complex features** (quiz engine, spaced repetition algorithm)
- ✅ **High test coverage needed** (learning analytics, adaptive logic)
- ✅ **Multiple adapters** (REST API + WebSocket + Server Actions)

#### When to Stay Simple?

- ❌ **Simple CRUD** (user profile, settings pages)
- ❌ **Presentation-only** (landing pages, marketing content)
- ❌ **Rapid prototyping** (MVP features, experiments)

**Recommended reading:** Next.js docs explicitly state the framework is ["unopinionated about how you organize files"](https://nextjs.org/docs/app/getting-started/project-structure), allowing teams to choose what works best.

---

## 📁 Project Structure

```
apps/web-app/
├── src/
│   ├── app/                           # Next.js 16 App Router (routing only)
│   │   ├── (public)/                  # Public routes (unauthenticated)
│   │   │   ├── page.tsx               # Landing page
│   │   │   ├── about/
│   │   │   ├── pricing/
│   │   │   └── features/
│   │   │
│   │   ├── (auth)/                    # Auth routes
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── forgot-password/
│   │   │
│   │   ├── (authenticated)/           # Protected routes (learner)
│   │   │   ├── dashboard/             # Overview, review queue, progress
│   │   │   ├── quiz/
│   │   │   │   ├── new/               # Start new quiz session
│   │   │   │   └── [sessionId]/       # Active quiz session
│   │   │   ├── memocards/
│   │   │   │   ├── decks/             # Memocard deck management
│   │   │   │   ├── review/            # Spaced repetition review
│   │   │   │   └── [deckId]/          # Individual deck view
│   │   │   ├── analytics/             # Personal learning analytics
│   │   │   │   ├── overview/
│   │   │   │   ├── mastery/           # Mastery progress by concept
│   │   │   │   └── sessions/          # Session history
│   │   │   ├── profile/               # User profile settings
│   │   │   └── feedback/              # Submitted feedback history
│   │   │
│   │   ├── (admin)/                   # Admin routes
│   │   │   ├── users/                 # User management
│   │   │   ├── system/                # System settings
│   │   │   └── reports/               # System-wide analytics
│   │   │
│   │   ├── (moderator)/               # Moderator routes
│   │   │   ├── questions/             # Question moderation
│   │   │   ├── flagged/               # Flagged content review
│   │   │   └── validation/            # Validation logs
│   │   │
│   │   ├── (analyst)/                 # Analyst routes
│   │   │   ├── insights/              # Data insights
│   │   │   └── exports/               # Data exports
│   │   │
│   │   ├── api/                       # API routes (Auth.js ONLY)
│   │   │   └── auth/
│   │   │       └── [...nextauth]/     # Auth.js v5 endpoints
│   │   │
│   │   └── layout.tsx                 # Root layout
│   │
│   ├── features/                      # 🎯 Feature-First Organization
│   │   ├── quiz/                      # Quiz feature (Clean Architecture)
│   │   │   ├── domain/                # Business logic & entities
│   │   │   │   ├── models/
│   │   │   │   │   ├── question.ts
│   │   │   │   │   └── quiz-session.ts
│   │   │   │   └── services/
│   │   │   │       └── scoring-engine.ts
│   │   │   ├── application/           # Use cases
│   │   │   │   ├── submit-answer.ts
│   │   │   │   ├── start-session.ts
│   │   │   │   └── get-hint.ts
│   │   │   ├── infrastructure/        # External dependencies
│   │   │   │   ├── api/
│   │   │   │   │   ├── quiz-api.ts    # TanStack Query calls
│   │   │   │   │   └── quiz-actions.ts # Server Actions
│   │   │   │   └── repositories/
│   │   │   │       └── quiz-repository.ts
│   │   │   ├── presentation/          # UI components
│   │   │   │   ├── components/
│   │   │   │   │   ├── question-card.tsx
│   │   │   │   │   ├── mcq-question.tsx
│   │   │   │   │   ├── fill-blank-question.tsx
│   │   │   │   │   ├── listening-question.tsx
│   │   │   │   │   ├── matching-question.tsx
│   │   │   │   │   ├── ordering-question.tsx
│   │   │   │   │   ├── progress-bar.tsx
│   │   │   │   │   ├── hint-button.tsx
│   │   │   │   │   └── feedback-modal.tsx
│   │   │   │   └── hooks/
│   │   │   │       ├── use-quiz-session.ts
│   │   │   │       └── use-quiz-timer.ts
│   │   │   └── index.ts               # Public API
│   │   │
│   │   ├── memocard/                  # Memocard feature (Clean Architecture)
│   │   │   ├── domain/
│   │   │   │   ├── models/
│   │   │   │   │   ├── card.ts
│   │   │   │   │   └── deck.ts
│   │   │   │   └── services/
│   │   │   │       └── spaced-repetition.ts # SM-2 algorithm
│   │   │   ├── application/
│   │   │   │   ├── review-card.ts
│   │   │   │   └── calculate-next-review.ts
│   │   │   ├── infrastructure/
│   │   │   │   ├── api/
│   │   │   │   │   └── memocard-api.ts
│   │   │   │   └── repositories/
│   │   │   │       └── deck-repository.ts
│   │   │   ├── presentation/
│   │   │   │   ├── components/
│   │   │   │   │   ├── flip-card.tsx
│   │   │   │   │   ├── memocard-deck.tsx
│   │   │   │   │   ├── review-session.tsx
│   │   │   │   │   ├── difficulty-buttons.tsx
│   │   │   │   │   └── card-stats.tsx
│   │   │   │   └── hooks/
│   │   │   │       ├── use-memocard-deck.ts
│   │   │   │       └── use-spaced-repetition.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── analytics/                 # Analytics feature (Clean Architecture)
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   ├── infrastructure/
│   │   │   ├── presentation/
│   │   │   │   └── components/
│   │   │   │       ├── mastery-chart.tsx
│   │   │   │       ├── progress-heatmap.tsx
│   │   │   │       ├── session-timeline.tsx
│   │   │   │       └── concept-graph.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── auth/                      # Auth feature (Simplified)
│   │   │   ├── components/
│   │   │   │   ├── login-form.tsx
│   │   │   │   └── register-form.tsx
│   │   │   ├── hooks/
│   │   │   │   └── use-auth.ts
│   │   │   └── index.ts
│   │   │
│   │   └── user-profile/              # User profile (Simplified)
│   │       ├── components/
│   │       ├── hooks/
│   │       └── index.ts
│   │
│   ├── shared/                        # 🌍 Shared across features
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn/ui primitives
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── dialog.tsx
│   │   │   │   └── ...
│   │   │   ├── audio/                 # Audio components
│   │   │   │   ├── audio-player.tsx
│   │   │   │   ├── tts-button.tsx
│   │   │   │   └── waveform-visualizer.tsx
│   │   │   ├── layout/                # Layout components
│   │   │   │   ├── header.tsx
│   │   │   │   ├── sidebar.tsx
│   │   │   │   ├── footer.tsx
│   │   │   │   └── role-based-nav.tsx
│   │   │   └── common/                # Common components
│   │   │       ├── loading-spinner.tsx
│   │   │       ├── error-boundary.tsx
│   │   │       ├── confetti-effect.tsx
│   │   │       └── image-zoom.tsx
│   │   │
│   │   ├── lib/                       # 🔧 Shared utilities
│   │   │   ├── api/
│   │   │   │   └── client.ts          # TanStack Query setup
│   │   │   ├── auth.ts                # Auth.js configuration
│   │   │   ├── audio.ts               # Howler.js wrapper
│   │   │   ├── utils.ts               # Utility functions (cn, formatters)
│   │   │   └── constants.ts           # App constants
│   │   │
│   │   ├── hooks/                     # 🪝 Global hooks
│   │   │   ├── use-audio.ts           # Audio playback
│   │   │   ├── use-keyboard-shortcuts.ts
│   │   │   ├── use-rbac.ts            # Role-based access control
│   │   │   └── use-media-query.ts
│   │   │
│   │   ├── stores/                    # Zustand stores
│   │   │   ├── user-prefs-store.ts    # User preferences (theme, audio)
│   │   │   └── notification-store.ts  # Toast notifications
│   │   │
│   │   └── types/                     # 📝 Shared types
│   │       ├── user.ts
│   │       └── api.ts                 # API response types
│   │
│   └── styles/
│       └── globals.css                # Global styles + Tailwind
│
├── public/
│   ├── sounds/                        # Audio assets
│   │   ├── correct.mp3
│   │   ├── incorrect.mp3
│   │   ├── flip.mp3
│   │   └── achievement.mp3
│   ├── images/                        # Static images
│   └── fonts/                         # Custom fonts (if any)
│
├── tailwind.config.ts                 # Tailwind configuration
├── next.config.js                     # Next.js configuration
├── tsconfig.json                      # TypeScript configuration
├── .env.example                       # Environment variables template
└── package.json
```

---

## 🎯 Architecture Patterns by Feature

| Feature             | Architecture       | Rationale                                             |
| ------------------- | ------------------ | ----------------------------------------------------- |
| **Quiz**            | Clean Architecture | Complex business logic (scoring, adaptive difficulty) |
| **Memocard**        | Clean Architecture | Spaced repetition algorithm, state machine            |
| **Analytics**       | Clean Architecture | Data transformation, multiple visualization layers    |
| **Auth**            | Simplified         | Mostly handled by Auth.js, minimal business logic     |
| **User Profile**    | Simplified         | Basic CRUD operations                                 |
| **Admin/Moderator** | Simplified         | Standard forms and tables                             |

---

## 🔑 Key Architectural Decisions

### 1. Feature-First Organization

Each feature is **self-contained** with its own domain logic, use cases, infrastructure, and presentation layers:

```tsx
// ✅ All quiz-related code lives together
import { QuestionCard, useQuizSession, submitAnswer } from '@/features/quiz';

// ❌ Instead of hunting across folders
import { QuestionCard } from '@/components/quiz/QuestionCard';
import { useQuizSession } from '@/hooks/useQuizSession';
import { submitAnswer } from '@/lib/api/quiz';
```

### 2. Clean Architecture for Complex Features

Inspired by [Lazar Nikolov's implementation](https://github.com/nikolovlazar/nextjs-clean-architecture), complex features follow the dependency rule:

```
presentation → application → domain
       ↓             ↓           ↑
infrastructure ←←←←←←←←←←←←←←←←←←←┘
```

**Example: Quiz Feature**

```tsx
// domain/services/scoring-engine.ts (Pure business logic)
export class ScoringEngine {
  calculateScore(answer: Answer, question: Question): Score {
    // No dependencies on UI, API, or frameworks
  }
}

// application/submit-answer.ts (Use case)
export async function submitAnswer(
  sessionId: string,
  answer: Answer,
  repository: QuizRepository // Injected dependency
): Promise<Result> {
  const question = await repository.getQuestion(sessionId);
  const score = new ScoringEngine().calculateScore(answer, question);
  await repository.saveScore(sessionId, score);
  return { score, feedback: generateFeedback(score) };
}

// infrastructure/repositories/quiz-repository.ts (API adapter)
export class QuizRepository {
  async getQuestion(sessionId: string): Promise<Question> {
    const res = await fetch(`${QUIZ_SERVICE_URL}/quiz/${sessionId}`);
    return res.json();
  }
}

// presentation/components/quiz-form.tsx (UI)
('use client');
export function QuizForm({ sessionId }: Props) {
  const mutation = useMutation({
    mutationFn: answer => submitAnswer(sessionId, answer, new QuizRepository()),
  });

  return <form onSubmit={mutation.mutate}>...</form>;
}
```

### 3. Direct Microservice Calls (No BFF)

The frontend calls backend microservices directly via TanStack Query and Server Actions:

```tsx
// ✅ Frontend → Microservice (via TanStack Query)
import { useQuery } from '@tanstack/react-query';

function useQuizSession(sessionId: string) {
  return useQuery({
    queryKey: ['quiz', sessionId],
    queryFn: async () => {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_QUIZ_SERVICE_URL}/quiz/${sessionId}`
      );
      return res.json();
    },
  });
}

// ✅ Frontend → Microservice (via Server Action)
('use server');
export async function startQuizSession(topicId: string) {
  const res = await fetch(`${process.env.QUIZ_SERVICE_URL}/quiz/start`, {
    method: 'POST',
    body: JSON.stringify({ topicId }),
  });
  return res.json();
}
```

### 4. API Routes ONLY for Auth.js

The `/api` folder is minimal - only authentication:

```
app/api/
└── auth/
    └── [...nextauth]/route.ts  # Auth.js v5 endpoints ONLY
```

**Backend microservices:**

- User management → `user-management-service` (port 3001)
- Quiz logic → `quiz-session-service` (port 3003)
- Learning engine → `learning-engine-service` (port 8000)
- Question generation → `question-generation-service` (port 8001)
- Analytics → `analytics-service` (port 3002)

Frontend calls these directly through NGINX API Gateway.

---

## 🚀 Getting Started

### Prerequisites

- **Node.js 20+**
- **pnpm 9+**

### Installation

```bash
pnpm install
cp .env.example .env.local
```

### Development

```bash
# Start dev server (port 3000)
pnpm dev

# Lint & format
pnpm lint && pnpm lint:fix && pnpm format

# Type check
pnpm type-check

# Test
pnpm test

# E2E tests
pnpm test:e2e

# Analyze bundle
pnpm analyze
```

---

## 🌍 Environment Variables

```env
# .env.local

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Auth.js v5
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-here

# AWS Cognito
COGNITO_CLIENT_ID=your-client-id
COGNITO_CLIENT_SECRET=your-client-secret
COGNITO_ISSUER=https://cognito-idp.region.amazonaws.com/poolId

# Microservices (Frontend calls these directly)
NEXT_PUBLIC_USER_SERVICE_URL=http://localhost:3001
NEXT_PUBLIC_QUIZ_SERVICE_URL=http://localhost:3003
NEXT_PUBLIC_LEARNING_ENGINE_URL=http://localhost:8000
NEXT_PUBLIC_QUESTION_GEN_URL=http://localhost:8001
NEXT_PUBLIC_ANALYTICS_SERVICE_URL=http://localhost:3002
NEXT_PUBLIC_CONTENT_SERVICE_URL=http://localhost:3004
NEXT_PUBLIC_NOTIFICATION_SERVICE_URL=http://localhost:3005

# Feature Flags
NEXT_PUBLIC_ENABLE_AUDIO=true
NEXT_PUBLIC_ENABLE_GAMIFICATION=true
```

---

## 📚 References & Inspiration

- **[Next.js Clean Architecture by Lazar Nikolov](https://github.com/nikolovlazar/nextjs-clean-architecture)** - Our primary architectural reference
- **[Next.js Official Docs - Project Structure](https://nextjs.org/docs/app/getting-started/project-structure)** - Framework conventions
- **[Vercel Examples](https://github.com/vercel/next.js/tree/canary/examples)** - Official patterns and best practices
- **Clean Architecture** by Robert C. Martin - Foundational principles

---

## 📝 Local Development

**Port:** 3000 (Next.js dev server)

**Backend Services:**

- User Service: `http://localhost:3001`
- Analytics Service: `http://localhost:3002`
- Quiz Service: `http://localhost:3003`
- Content Service: `http://localhost:3004`
- Notification Service: `http://localhost:3005`
- Learning Engine: `http://localhost:8000`
- Question Generation: `http://localhost:8001`

---

## 📄 License

See [LICENSE](../../LICENSE)
