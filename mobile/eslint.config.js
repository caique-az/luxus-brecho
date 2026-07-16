// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['dist/*', 'node_modules/*', '**/*.d.ts'],
  },
  {
    files: ['**/*.{ts,tsx}'],
    rules: {
      // TypeScript specific rules
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': 'error',
      // prefer-const é regra do core (declarada abaixo). Não existe no plugin
      // @typescript-eslint — declará-la aqui derrubava o eslint inteiro com
      // "Could not find prefer-const in plugin", e nenhum lint rodava.
      '@typescript-eslint/no-non-null-assertion': 'warn',
      
      // React specific rules
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      'react/prop-types': 'off', // We use TypeScript for prop validation
      
      // General code quality
      'no-console': 'warn',
      'prefer-const': 'error',
      'no-var': 'error',
      'eqeqeq': 'error',
      'curly': 'error',
      
      // Performance
      'react/jsx-key': 'error',
      'react/no-array-index-key': 'warn',
      
      // Security
      'no-eval': 'error',
      'no-implied-eval': 'error',
    },
  },
  {
    files: ['**/*.test.{ts,tsx}', '**/__tests__/**/*.{ts,tsx}'],
    rules: {
      // Allow console in tests
      'no-console': 'off',
      // Allow any in tests for mocking
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
]);
