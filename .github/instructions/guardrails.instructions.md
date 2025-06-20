# Guard Rails: AI Productivity App

This document outlines mandatory guard rails (constraints, standards, and best practices) for contributing to, deploying, and operating the AI Productivity App. Adhering to these guidelines is essential for maintaining security, stability, code quality, and user trust.

---

## Single Sources of Truth (SSOT)

The following are implementation-verified single sources of truth. All contributors MUST reference and update these concrete sources, as established in code, to avoid duplication, drift, or ambiguity in business logic, configuration, data, and application state.

### Backend SSOTs

- **Application Configuration**
  - [`Settings`](../backend/app/config.py#L12) class in [`backend/app/config.py`](../backend/app/config.py):
    - Loads all runtime configuration for the backend from environment variables using Pydantic.
    - All environment-driven logic must derive from this class.
    - Any new config must be added as a field to `Settings` and documented in `.env.example`.

- **Database Models (Authoritative Data Schema)**
  - SQLAlchemy model classes in [`backend/app/models/`](../backend/app/models/):
    - [`User`](../backend/app/models/user.py), [`Project`](../backend/app/models/project.py), [`ChatSession`](../backend/app/models/chat.py), [`CodeDocument`](../backend/app/models/code.py), [`Session`](../backend/app/models/session.py), etc.
    - These classes define the full canonical persisted data shape for all project entities.
    - Any database change must update both the ORM class and generate a corresponding migration in [`backend/alembic/versions/`](../backend/alembic/versions/).

- **Core Business Logic and Validation**
  - Validation and business rules present in model methods and service modules (`backend/app/services/`).
  - For example: field-level `@validates` methods in [`Project`](../backend/app/models/project.py), [`ChatMessage`](../backend/app/models/chat.py), etc.
  - All business/process rules must reside here, not as duplicated frontend or adhoc logic.

### Frontend SSOTs

- **Project State (React/Zustand Store)**
  - [`useProjectStore`](../frontend/src/stores/projectStore.js) in [`frontend/src/stores/projectStore.js`](../frontend/src/stores/projectStore.js):
    - Manages all canonical project data, filters, and state updates in the React app.
    - All features dealing with projects *must* utilize this store as the source of state and perform state mutations through defined store actions.

- **User Auth & Preferences State**
  - Auth/session/prefs managed in [`frontend/src/stores/authStore.js`](../frontend/src/stores/authStore.js):
    - Holds single source for user session metadata and persistent preferences.
    - Any changes to auth/session logic must update this store.

### Global/Platform SSOTs

- **Environment and Secret Management**
  - Actual configuration values and secrets live in:
    - [`ai-productivity-app/.env`](../.env), [`ai-productivity-app/.env.example`](../.env.example), [`ai-productivity-app/backend/.env`](../backend/.env), [`ai-productivity-app/frontend/.env`](../frontend/.env)
    - **Never** copy or partially duplicate these values in code or in documentation.

### Documentation SSOT

- **Team/Public Process/Architecture**
  - Markdown documents in [`docs/`](../docs/), including [`GUARDRAILS.md`](GUARDRAILS.md).
  - Process and operational changes must be reflected here and tied to their technical SSOT references.

---

**Risks of Violating These SSOTs:**
- Configuration drift
- Silent application errors
- Broken contract or API drift
- Security vulnerabilities
- Inconsistent UX/business logic

**Mandate:**
All pull requests or changes impacting these artifacts *must* explicitly reference the affected SSOT(s) in their description or changelogs. Any implementation ambiguity must be triaged by examining these concrete sources in code.

---

## 1. Code Quality & Standards

- **Style Guides:**
  - **Python:** Follow [PEP8](https://www.python.org/dev/peps/pep-0008/) and enforce with `pylint`/`black`/`ruff`.
  - **JavaScript/React:** Follow [Airbnb JS](https://github.com/airbnb/javascript) or ESLint-configured repo guidelines.
- **Type Safety:**
  - Use type hints for Python (mypy when possible).
  - Apply TypeScript or JSDoc in React as appropriate.
- **Code Reviews:**
  - All code changes MUST be peer-reviewed via Pull Requests.
  - Automated linting and formatting checks must pass before merge.
- **Documentation:**
  - All public-facing functions, classes, and API endpoints must have docstrings or JSDoc.
  - Update and maintain docs in `/docs` for feature changes.

---

## 2. Security Practices

- **Secret Management:**
  - **Never commit secrets:** API keys, credentials, and private keys MUST NOT be committed to source control. Use environment variables or secret stores.
  - Use `.env.example` to document required env vars.
- **Authentication & Authorization:**
  - All backend endpoints must check authentication and enforce least privilege.
  - Admin actions require elevated permissions and justification.
  - Support for 2FA and strong password requirements for user accounts.
- **Dependency Management:**
  - Use `pip-audit`, `npm audit`, or equivalent to scan for vulnerabilities before merging or releasing.
  - No direct installs from untrusted sources.
- **Input Validation & Sanitization:**
  - All user-generated data must be strictly validated and sanitized on backend and frontend.
- **Vulnerability Disclosure:**
  - Promptly triage and remediate discovered vulnerabilities per the [ISSUE_REMEDIATION_PLAN.md](./ISSUE_REMEDIATION_PLAN.md).

---

## Critical Application Logic That Must Be Respected

The following application logic patterns and modules are essential for the correct, secure operation of the system. Any major feature, refactor, or integration must preserve or extend these mechanisms as implemented:

### Backend (Python/FastAPI)

- **API Endpoint Contracts:**
  - All route definitions in [`backend/app/routers/`](../backend/app/routers/) (e.g., `auth.py`, `projects.py`, `chat.py`, `code.py`) contain parameter validation, role enforcement, and error handling. Do not bypass these contract layers with direct DB/script access.
- **Authentication, Sessions, and Security:**
  - Token issuance and session management logic is centralized in [`auth.py`](../backend/app/routers/auth.py).
  - **SecurityHeadersMiddleware** ([`security.py`](../backend/app/middleware/security.py)): Enforces required security headers and CSRF validation on every request.
  - **CORS** ([`cors.py`](../backend/app/middleware/cors.py)): Only origins allowed by `Settings.cors_origins_list` are permitted access.
  - **Rate-limiting:** Rate limits are enforced and handled via `_rate_limit_handler` in [`security.py`](../backend/app/middleware/security.py).
- **Permissions and Roles:**
  - Permission enforcement, including admin-only routes and user-specific access, must remain in place as defined in router and service logic.
- **Business Logic — Not Just in Models:**
  - Service-layer enforcement and cross-entity business rules reside in [`backend/app/services/`](../backend/app/services/). Refactor with care to maintain process integrity.
- **WebSocket Safety:**
  - Websocket endpoints in [`chat.py`](../backend/app/routers/chat.py) and [`notifications.py`](../backend/app/routers/notifications.py) must always perform auth and session checks before pushing/receiving any data.

### Frontend (React/JS)

- **Authentication and Access Gating:**
  - `useRequireAuth` in [`useAuth.js`](../frontend/src/hooks/useAuth.js) must be used to protect any page/component that requires login; do not manually implement custom guards.
- **Data Loading and Canonical State:**
  - Loading, filtering, and updating of project/chat/search state must route through canonical hooks such as:
    - [`useProject`](../frontend/src/hooks/useProjects.js), [`useProjectSearch`](../frontend/src/hooks/useProjects.js), [`useProjectTimeline`](../frontend/src/hooks/useProjects.js)
    - [`useChat`](../frontend/src/hooks/useChat.js) for all chat-related actions and initialization
    - [`useConfig`](../frontend/src/hooks/useConfig.js) for configuration-driven UI/feature flags
- **Persistent/Shared State:**
  - All shared/user state must route through their zustand stores (`projectStore.js`, `authStore.js`).
- **Error Boundaries and Theming:**
  - Core providers like [`ThemeProvider`](../frontend/src/hooks/useTheme.jsx) and any error boundaries must wrap application entrypoints.

### Cross-Cutting

- **Never Bypass Middleware:**
  - Security, logging, and CORS middleware are always in force. All HTTP endpoints, even internal APIs, must pass through these chains.
- **No Direct DB or Store Modification:**
  - All writes must go through validated service, router, or store interfaces. Never mutate the database or frontend global state directly from view/UI code or scripts.

These layers collectively enforce application invariants, trust boundaries, and security requirements.

---

## 3. Data Privacy & Usage

- **Personal Data:**
  - Collect only necessary data; annotate any new PII fields and justify storage.
  - User data exports and deletions must be supported per applicable privacy regulations (GDPR, etc.).
- **Logging:**
  - Never log secrets or sensitive data. Audit logs for authentication and admin actions only.
- **Data Access:**
  - Use strict ORM queries to avoid unintentional data exposure or leaks.

---

## 4. Testing & Validation

- **Automated Testing:**
  - All business logic must be covered by unit and integration tests.
  - Use Pytest for Python; Jest/React Testing Library for JS.
- **Test Coverage:**
  - Minimum 80% code coverage goal, enforced in CI.
- **Manual validation:**
  - Major feature changes require manual QA checks for security and UX.

---

## 5. Infrastructure & Deployment

- **CI/CD Pipelines:**
  - All merges to `main` must pass full test, lint, and build pipelines.
  - Staging environment required; never deploy untested changes to production.
- **Containerization:**
  - Use Docker and Docker Compose for environments; check Dockerfiles for best practices and minimal images.
- **Environment Parity:**
  - Staging and production environments should mirror each other closely (services, config, secrets).

---

## 6. API & Integration

- **External APIs:**
  - All third-party integrations require threat model review.
  - Validate all responses received from external APIs.
- **Rate Limits:**
  - Implement and respect sensible rate limits for all public endpoints.
- **Error Handling:**
  - Never expose internal errors or stack traces publicly; log internally and return generic messages to clients.

---

## 7. Contribution Process

- **Pull Requests:**
  - PRs must link to an issue or describe their intent clearly.
- **Commit Messages:**
  - Use conventional commit messages (`feat:`, `fix:`, `docs:`, etc.).
- **Issue Templates:**
  - All issues (bugs/features) must use templates with clear reproduction steps or acceptance criteria.

---

## 8. Operational Guard Rails

- **Monitoring & Alerts:**
  - Set up monitoring (CPU, RAM, health, error rates) on all production components.
  - Alerting must be enabled for failure, downtime, or suspicious actions.
- **Backups & Disaster Recovery:**
  - Implement regular automated backups for all persistent data stores.
- **Incident Response:**
  - Define escalation steps and contacts for out-of-hours or critical incidents.

---

## 9. Prohibited Practices

- Never bypass authentication or privilege checks for expedience.
- No feature toggling via untracked ad-hoc settings in production.
- Do not merge code with failing tests or security checks.
- Do not store business logic in database migrations or one-off scripts.

---

## 10. Periodic Review & Updating

- This guard rails document must be reviewed and updated at least quarterly, or after major product/technology shifts.
- All team members are responsible for compliance. Non-compliance may result in access restrictions or removal from the project.

---
