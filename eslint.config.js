import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';

let nextPlugin;
try {
  nextPlugin = (await import('@next/eslint-plugin-next')).default;
} catch {
  nextPlugin = null;
}

const FILES = ['**/*.{ts,tsx,js,jsx}'];

const IGNORES = [
  '**/node_modules/**',
  '**/.next/**',
  '**/dist/**',
  '**/build/**',
  '**/coverage/**',
  '**/.venv/**',
  '**/*.config.js',
  '**/*.config.ts',
  '**/*.d.ts',
  '**/.eslintrc*',
  '**/*.json',
  '**/generated/**',
  '**/public/**',
  'packages/migration-service/knexfile.js',
];

export default [
  { ignores: IGNORES },
  { ...js.configs.recommended, files: FILES },
  ...tseslint.configs.recommended.map(config => ({ ...config, files: FILES })),
  {
    files: FILES,
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.es2020,
        React: 'readonly',
      },
    },
    plugins: {
      ...(nextPlugin && { '@next/next': nextPlugin }),
    },
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_|^__' },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/ban-ts-comment': 'warn',
      '@typescript-eslint/no-empty-object-type': 'warn',
      '@typescript-eslint/no-require-imports': 'warn',
      'no-console': ['warn', { allow: ['warn', 'error', 'info', 'log'] }],
      'no-undef': 'warn',
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    rules: { 'no-undef': 'off' },
  },
];
