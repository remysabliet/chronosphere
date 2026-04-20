# 🗺️ Route Architecture for Memosphere Engine

Based on your microservice architecture, here's the recommended route structure:

---

## 🌐 Public Routes (`/`)

These routes are accessible without authentication:

```
/                          → Landing page with value proposition
/about                     → About the platform and methodology
/features                  → Feature showcase (BKT, adaptive learning, etc.)
/pricing                   → Pricing tiers (if applicable)
/demo                      → Interactive demo or sample quiz
/login                     → Login page
/register                  → Registration page
/forgot-password           → Password recovery
/verify-email/:token       → Email verification
/terms                     → Terms of service
/privacy                   → Privacy policy
```

---

## 🔐 Private Routes (Authenticated Users)

### Learner Routes (`/app`)

```
/app/dashboard             → Personal dashboard with progress overview
/app/profile               → Profile settings and preferences
/app/subjects              → Browse available subjects/topics
/app/subjects/:id          → Subject detail page with concepts
```

#### Quiz & Learning Flow

```
/app/quiz/start            → Quiz initialization (select thema/concepts)
/app/quiz/:sessionId       → Active quiz session
/app/quiz/:sessionId/review → Post-session review and feedback
```

#### Progress & Analytics

```
/app/progress              → Detailed progress tracking
/app/mastery               → Mastery status across concepts
/app/history               → Session history and past performance
/app/review-queue          → Spaced repetition review queue
```

#### Settings

```
/app/settings              → Account settings
/app/notifications         → Notification preferences
```

---

### Admin Routes (`/admin`)

```
/admin/dashboard           → Admin overview (system health, metrics)
/admin/users               → User management
/admin/users/:id           → User detail and role assignment
/admin/content             → Content management system
/admin/subjects            → Manage subjects and taxonomy
/admin/concepts            → Concept library management
/admin/analytics           → System-wide analytics
/admin/settings            → Platform configuration
/admin/audit-logs          → System audit logs
```

#### Question Quality Monitoring

```
/admin/questions           → Question library overview
/admin/questions/flagged   → Auto-flagged questions (low performance, validation failures)
/admin/questions/reported  → Learner-reported questions with issue descriptions
/admin/questions/:id       → Question detail view with full analytics
/admin/questions/retired   → Questions removed from rotation
/admin/questions/stats     → Question quality metrics dashboard
```

#### System Logs & Debugging

```
/admin/logs                → Error logs, system events
/admin/logs/ai-generation  → AI question generation logs (failures, retries)
/admin/logs/validation     → Validation failures and patterns
/admin/health              → Service health checks, API response times, database status
```

#### AI Configuration

```
/admin/ai-config           → AI model settings (prompts, temperature, tokens)
```

---

## 🏗️ Route Organization Strategy

### Route Grouping by Feature

```
/app/*          → Learner experience
/admin/*        → Platform administration
/api/*          → API endpoints (if exposing public API)
```

### Protected Route Middleware Chain

```
Public          → No auth required
/app/*          → Requires: Authentication
/admin/*        → Requires: Authentication + Admin role
```

---

## 🎯 Special Considerations

### Deep Linking for Quiz Sessions

```
/app/quiz/:sessionId/question/:questionIndex
```

This allows learners to bookmark or share their position (useful for long sessions).

### Shareable Progress

```
/share/progress/:userId/:token  → Public shareable progress card
```

### API Routes (if building mobile app or exposing API)

```
/api/v1/auth/*
/api/v1/quiz/*
/api/v1/analytics/*
/api/v1/content/*
```

### 404 & Error Pages

```
/404                      → Not found
/500                      → Server error
/maintenance              → Maintenance mode
```

---

## 🔄 Navigation Flow Examples

### New User Journey

```
/ (landing)
  → /register
  → /verify-email
  → /login
  → /app/dashboard
  → /app/subjects
  → /app/quiz/start
  → /app/quiz/:sessionId
  → /app/quiz/:sessionId/review
  → /app/dashboard
```

### Returning Learner

```
/login
  → /app/dashboard
  → /app/review-queue
  → /app/quiz/:sessionId
  → /app/mastery
```

---

## 💡 Best Practices Applied

1. **Clear hierarchy**: Public → Authenticated → Role-based
2. **Predictable patterns**: RESTful naming conventions
3. **Scoped namespaces**: `/app`, `/admin` prevent route collisions
4. **Stateful sessions**: Quiz routes include `sessionId` for state persistence
5. **Semantic URLs**: Routes reflect user intent and mental models
6. **Security by design**: Sensitive routes grouped under protected namespaces

---

## 🎯 Minimal Admin Actions

You only manually intervene when:

1. **AI flags something suspicious** → Quick review in `/admin/questions/:id`
2. **Multiple learner reports** → Investigate in `/admin/questions/reported`
3. **System errors spike** → Debug in `/admin/logs`
4. **New subject launch** → Add concepts in `/admin/concepts`

**Most days?** Zero admin work needed. The system runs itself. 🚀
