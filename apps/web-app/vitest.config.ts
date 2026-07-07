import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    include: ['tests/**/*.test.{ts,tsx}'],
    globals: true,
    environment: 'node',
    setupFiles: ['./tests/setup.ts'],
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
    // Mirrors tsconfig.json's `paths` — order matters, the specific `@/x/*`
    // entries must be checked before the catch-all `@/*` or they'd never match.
    alias: [
      {
        find: '@/components',
        replacement: path.resolve(__dirname, 'src/shared/components'),
      },
      {
        find: '@/ui',
        replacement: path.resolve(__dirname, 'src/shared/components/ui'),
      },
      {
        find: '@/features',
        replacement: path.resolve(__dirname, 'src/features'),
      },
      { find: '@/lib', replacement: path.resolve(__dirname, 'src/shared/lib') },
      {
        find: '@/hooks',
        replacement: path.resolve(__dirname, 'src/shared/hooks'),
      },
      {
        find: '@/stores',
        replacement: path.resolve(__dirname, 'src/shared/stores'),
      },
      {
        find: '@/types',
        replacement: path.resolve(__dirname, 'src/shared/types'),
      },
      { find: '@/styles', replacement: path.resolve(__dirname, 'src/styles') },
      { find: '@', replacement: path.resolve(__dirname, 'src') },
    ],
  },
});
