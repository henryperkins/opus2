## Phase 3 – Project Management (2025-05-31)

- Major: Adds project CRUD, status, color, emoji, tags, timeline event tracking, filtering/search.
- Backend:
  - REST API: `/api/projects`, `/api/projects/{id}`, `/api/projects/{id}/timeline`
  - Alembic migration for new fields and timeline_events table.
  - New config: see `.env.example`.
  - Pytest suite for project flows (CRUD, timeline, search, auth, >90% cov).
- Frontend:
  - Projects dashboard, cards, filters, modals, timeline visualization.
  - Zustand store with optimistic updates.
  - Custom hooks for project fetch/search/timeline.
- Docs: API reference, setup, and migration docs extended.
- This release requires running the new Alembic migration and populating env variables as described.

---
