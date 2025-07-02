import js from '@eslint/js';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

export default [
  {
    files: ['**/*.{js,jsx}'],
    ignores: ['**/*.test.{js,jsx}', '**/test/**', '**/tests/**', '**/api/client.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: {
          jsx: true
        }
      }, globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        process: 'readonly',
        Buffer: 'readonly',
        global: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        CustomEvent: 'readonly',
        FormData: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        navigator: 'readonly',
        fetch: 'readonly',
        URLSearchParams: 'readonly',
        URL: 'readonly',
        location: 'readonly',
        history: 'readonly',
        btoa: 'readonly',
        atob: 'readonly',
        WebSocket: 'readonly',
        performance: 'readonly',
        IntersectionObserver: 'readonly',
        Blob: 'readonly',
        monaco: 'readonly',
        alert: 'readonly'
      }
    },
    plugins: {
      react,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh
    },
    rules: {
      ...js.configs.recommended.rules,
      // Disallow raw axios usage in components to enforce API layer and hooks
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: 'axios',
              message: 'Use frontend/src/api/client.js or React-query hooks instead of importing axios directly.'
            }
          ],
          patterns: [
            {
              group: ['../api/*', './api/*'],
              message: 'Components should call hooks, not API modules directly.'
            }
          ]
        }
      ],
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'warn',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      'react-refresh/only-export-components': 'warn',
      'no-unused-vars': 'warn'
    },
    settings: {
      react: {
        version: 'detect'
      }
    }
  },
  {
    // Allow hooks and state stores to import from the API layer – they belong
    // to the data-access abstraction, unlike UI components that should depend
    // on hooks/stores only.
    files: ['**/hooks/**/*.{js,jsx}', '**/stores/**/*.{js,jsx}'],
    rules: {
      'no-restricted-imports': 'off'
    }
  },
  {
    files: ['**/*.test.{js,jsx}', '**/test/**/*.{js,jsx}', '**/tests/**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: {
          jsx: true
        }
      },
      globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        beforeAll: 'readonly',
        afterAll: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        describe: 'readonly',
        it: 'readonly',
        test: 'readonly',
        expect: 'readonly',
        vi: 'readonly',
        vitest: 'readonly',
        jest: 'readonly'
      }
    },
    rules: {
      'no-unused-vars': 'warn',
      'react/prop-types': 'off'
    }
  },
  {
    // API layer files are allowed to import axios and other modules directly
    files: ['**/api/**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        process: 'readonly',
        fetch: 'readonly',
        FormData: 'readonly',
        URLSearchParams: 'readonly',
        URL: 'readonly'
      }
    },
    rules: {
      'no-restricted-imports': 'off',
      'no-unused-vars': 'warn'
    }
  }
];
