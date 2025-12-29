import js from '@eslint/js'
import tseslint from 'typescript-eslint'

let nextPlugin
try {
  nextPlugin = (await import('@next/eslint-plugin-next')).default
} catch {
  nextPlugin = null
}

export default [
  {
    ignores: [
      'node_modules',
      '.next',
      'dist',
      'build',
      '**/*.config.js',
      '**/coverage',
      'packages/migration-service/knexfile.js',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['**/*.{ts,tsx,js,jsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      globals: {
        document: 'readonly',
        window: 'readonly',
        console: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        process: 'readonly',
        Buffer: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
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
]