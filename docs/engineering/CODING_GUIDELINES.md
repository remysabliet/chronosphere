# Coding Guidelines

## Git Workflow

### Branch Naming Convention

Format: `<type>/<short-description>`

**Types:**

- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `style/` - Code style/formatting (no logic changes)
- `refactor/` - Code refactoring
- `perf/` - Performance improvements
- `test/` - Adding/updating tests
- `chore/` - Maintenance tasks (dependencies, configs)

**Examples:**

```
feat/user-authentication
fix/quiz-scoring-bug
docs/api-endpoints
refactor/database-queries
```

### Commit Message Convention

Format: `<emoji> <type>: <description>`

**Commit Types with Emojis:**

- ✨ `feat:` - New feature
- 🐛 `fix:` - Bug fix
- 📚 `docs:` - Documentation
- 💄 `style:` - Formatting, semicolons, etc.
- ♻️ `refactor:` - Code refactoring
- ⚡ `perf:` - Performance improvement
- ✅ `test:` - Adding/updating tests
- 🔧 `chore:` - Maintenance, dependencies
- 🚀 `deploy:` - Deployment-related
- 🔒 `security:` - Security improvements
- 🗃️ `db:` - Database changes
- 🎨 `ui:` - UI/UX improvements

**Examples:**

```
✨ feat: Add user authentication with OAuth
🐛 fix: Resolve quiz scoring calculation error
📚 docs: Update API endpoint documentation
♻️ refactor: Simplify database query logic
✅ test: Add unit tests for learning engine
```

### Branch Strategy

**Main Branches:**

- `main` - Production-ready code
- `develop` - Integration branch for features

**Workflow:**

1. Create feature branch from `develop`: `feat/new-feature`
2. Make changes and commit with proper format
3. Push and create PR to `develop`
4. After review, merge to `develop`
5. Periodically merge `develop` → `main` for releases

**Protected Branches:**

- `main` - Requires PR + approval
- `develop` - Requires PR + passing tests

## Code Style

### TypeScript/JavaScript

**General:**

- Use TypeScript strict mode
- Prefer `const` over `let`, avoid `var`
- Use arrow functions for callbacks
- Destructure props and objects
- Use optional chaining `?.` and nullish coalescing `??`

**Naming:**

- **Variables/Functions:** camelCase (`getUserData`, `isActive`)
- **Components:** PascalCase (`UserProfile`, `QuizCard`)
- **Constants:** UPPER_SNAKE_CASE (`API_URL`, `MAX_RETRIES`)
- **Files:** kebab-case (`user-profile.tsx`, `quiz-utils.ts`)

**Imports Order:**

1. External libraries (React, Next.js, etc.)
2. Internal absolute imports (`@/components`, `@/lib`)
3. Relative imports (`./`, `../`)

**React:**

- Use functional components with hooks
- Client components: add `'use client'` directive
- Server components: default (no directive needed)
- Avoid inline functions in JSX (extract to constants)

### Python

**General:**

- Follow PEP 8
- Type hints for all functions
- Use Black formatter (80 char line length)
- Use isort for import sorting

**Naming:**

- **Variables/Functions:** snake_case (`get_user_data`, `is_active`)
- **Classes:** PascalCase (`UserProfile`, `QuizEngine`)
- **Constants:** UPPER_SNAKE_CASE (`API_URL`, `MAX_RETRIES`)

## Testing

**Requirements:**

- Write tests for all new features
- Minimum 80% code coverage
- Run tests before pushing: `pnpm test`

**Test Types:**

- Unit tests: `tests/unit/**/*.test.ts`
- Integration tests: `tests/integration/**/*.test.ts`
- E2E tests: Playwright

## Pre-Commit Checks

Automatically enforced by Husky:

**Pre-Commit:**

1. Lint check (`pnpm lint`)
2. Format check (`pnpm format`)

**Pre-Push:**

1. Type check (`pnpm type-check`)
2. Unit tests (`pnpm test:unit`)
3. Branch name validation

## File Organization

```
src/
├── app/              # Next.js App Router
├── features/         # Feature modules
├── shared/
│   ├── components/   # Reusable components
│   │   ├── ui/       # shadcn/ui primitives
│   │   └── layout/   # Layout components
│   ├── lib/          # Utilities
│   ├── hooks/        # Custom hooks
│   ├── stores/       # State management
│   └── types/        # TypeScript types
└── styles/           # Global styles
```

## Comments

- Write self-documenting code
- Add comments only for complex logic
- Use JSDoc for public APIs
- Avoid obvious comments

**Good:**

```typescript
// Calculate BKT probability using prior knowledge and evidence
const probability = calculateBKTProbability(prior, evidence);
```

**Bad:**

```typescript
// Set x to 5
const x = 5;
```

## Pull Requests

**Requirements:**

- Clear description of changes
- Link to related issue/ticket
- Screenshots for UI changes
- All checks passing
- At least 1 approval

**PR Title Format:**

```
<emoji> <type>: <description>
```

Example: `✨ feat: Add OAuth authentication flow`
