import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    include: ['tests/**/*.test.{ts,tsx}'],
    globals: true,
    environment: 'node',
    coverage: {
      provider: 'v8',
      // Only measure coverage on pure logic — pages/components/server actions
      // require integration or E2E tests (Next.js runtime, auth sessions, etc.)
      include: ['src/shared/lib/**/*.ts'],
      // auth.ts (NextAuth config) and thema-actions.ts (Next.js server actions
      // that depend on auth() + fetch) are excluded — they require Next.js
      // runtime context; cover them with integration/E2E tests instead.
      exclude: ['src/shared/lib/auth.ts', 'src/shared/lib/actions/**'],
      thresholds: { lines: 80 },
      reporter: ['text', 'lcov'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
});
