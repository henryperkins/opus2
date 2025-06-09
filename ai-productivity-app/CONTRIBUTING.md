# Contributing Guide

Thank you for taking the time to contribute to **Opus 2**!  We love all kinds of
contributions – bug fixes, new features, documentation, and tests.

## Pull-Request Checklist

Please make sure every PR:

1. **Has an issue or ticket** reference in the description.
2. **Adds or updates unit tests** for any functional change.
3. **Passes CI locally** (`docker compose up`, `pytest -q`, `npm run lint`).
4. **Includes Sentry tags** (`span.set_tag('project_id', …)` & `user_id`) where
   new API endpoints or long-running tasks are introduced.
5. **Updates docs** (`docs/`, OpenAPI schemas, or Storybook) when behaviour or
   API surface changes.
6. Uses **Conventional Commits** style (`feat:`, `fix:`, `chore:` …).

## Development Quick-Start

```bash
# Backend
cd backend
poetry install
pytest -q

# Frontend
cd ../frontend
npm ci
npm run dev
```

## Type Safety & Linting

* **Python:** `mypy --strict` runs in CI.  Add precise type hints and fix any
  new errors before submitting.
* **JavaScript/React:** `npm run lint` (ESLint) runs with
  `--max-warnings=0`.  Warnings are treated as errors in CI to keep the code
  base clean.

## Code Style

* Python is formatted with **black** & import-sorted with **isort**.
* Frontend uses **Prettier** (via your editor) & ESLint for consistency.

Thank you again – happy coding! 🚀
