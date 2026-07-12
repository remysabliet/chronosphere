# Code Review Checklist

When reviewing any code change (PR review, diff review, or on request), run and report on the following checks for all modified files.

## Python files (`*.py`)

```bash
# Lint + auto-fix (run from repo root — ruff.toml is auto-discovered)
uvx ruff check --fix <files>
uvx ruff format <files>

# Type check — run per affected service using its own venv
cd packages/question-generation-service && uv run pyright .
cd packages/learning-engine-service     && poetry run pyright .
cd packages/shared-python               && uv run pyright .
```

Report: any unfixable ruff violations, any pyright type errors.

## TypeScript / JavaScript files (`*.ts`, `*.tsx`, `*.js`, `*.jsx`)

```bash
# Lint + auto-fix (run from repo root)
pnpm exec eslint --fix <files>

# Type check — run per affected workspace
cd apps/web-app && pnpm exec tsc --noEmit
# For Node.js service stubs, type-check is covered by tsc at root:
pnpm run type-check
```

Report: any unfixable ESLint violations, any TypeScript errors.

## When to run

- **Before starting any PR review**: auto-fix all linting issues first, then report remaining errors.
- After writing or modifying any code, before marking a task done.
- If a user asks "does this have lint errors?" or similar.

## Auto-fix workflow (mandatory before PR review)

1. Run `uvx ruff check --fix` + `uvx ruff format` on all changed `.py` files.
2. Run `pnpm exec eslint --fix` on all changed `.ts/.tsx/.js/.jsx` files.
3. Re-stage any fixed files.
4. Then run pyright + tsc and report remaining errors that require manual fixes.
