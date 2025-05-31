## Phase 3: Project Management – Setup and Migration

This release adds full project management capabilities with CRUD, status, timeline, tags, color/emoji, filtering/search, and full REST API coverage.

### Migration steps

1. Ensure you have pulled the latest code.
2. Run new database migration:

   ```
   alembic upgrade head
   ```

3. Review or update `.env.example` for the following (see full .env for more options):

   ```
   # Project management phase 3
   PROJECT_FEATURES_ENABLED=true
   PROJECTS_PAGINATION_DEFAULT=20
   PROJECTS_PAGINATION_MAX=100
   ```

4. Run backend tests to verify functionality:

   ```
   pytest tests/test_projects.py
   ```

5. See [../docs/API.md](../docs/API.md) for full API endpoint details.

### Features

- Create/read/update/delete projects
- Status, color, emoji, tags, timeline/history
- Filter and search projects by any field
- Fully type-safe REST API, secure via authentication
- All endpoints and business logic fully tested

---
