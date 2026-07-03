# Shared Package

Common utilities, types, schemas, and configurations for all Memosphere microservices.

## Structure

```
src/
├── types/           # TypeScript interfaces
├── schemas/         # Zod validation schemas
├── constants/       # App constants (roles, permissions)
├── utils/           # Helper functions
└── config/          # Shared configurations
```

## Usage

```typescript
import { User, UserRole, USER_ROLES } from '@memosphere/shared';
import { UserSchema } from '@memosphere/shared/schemas';
import { validateEmail } from '@memosphere/shared/utils';
```

## Key Exports

- **Types**: User, Quiz, Analytics, BKT/IRT interfaces
- **Constants**: User roles, permissions, Bloom levels
- **Schemas**: Zod validation for APIs
- **Utils**: Validation, formatting, crypto functions

## Development

```bash
pnpm test
pnpm build
```

## Testing

```bash
# Run tests with coverage (requires ≥80% line coverage)
pnpm test:coverage

# Run tests in watch mode
pnpm test
```

Tests live in `tests/unit/` and cover the `src/index.ts` barrel exports (auth utilities). Coverage uses vitest + @vitest/coverage-v8.

## Usage in Services

This package is consumed by other services - no standalone port needed.
