# Phase 2 Implementation Plan: Authentication & User Management

## Overview
Phase 2 implements core authentication functionality for the AI Productivity App, focusing on practical solutions for a small team of 2-3 users. This phase prioritizes simplicity and security without over-engineering.

## Timeline: 2 Weeks (10 Business Days)

## Objectives
1. Implement secure user authentication with JWT tokens
2. Create login/registration functionality
3. Add session management and protected routes
4. Integrate authentication across frontend and backend

## Technical Approach
- **Backend**: FastAPI with JWT tokens, bcrypt password hashing
- **Frontend**: React with context-based auth state management
- **Storage**: SQLite with existing User model
- **Security**: HttpOnly cookies, CSRF protection, secure sessions

---

## Week 1: Backend Authentication (Days 1-5)

### Day 1-2: Core Authentication Infrastructure

**Tasks:**
1. Create authentication security module
2. Implement JWT token generation and validation
3. Add password hashing utilities
4. Create user session management

**Deliverables:**

`backend/app/auth/security.py` (≤200 lines)
```python
# JWT token creation/validation
# Password hashing with bcrypt
# Session token management
# Token refresh logic
```

`backend/app/auth/schemas.py` (≤150 lines)
```python
# Pydantic models for:
# - UserLogin
# - UserRegister
# - TokenResponse
# - UserResponse
```

`backend/app/auth/utils.py` (≤100 lines)
```python
# get_current_user dependency
# verify_credentials helper
# create_session helper
```

### Day 3-4: Authentication Endpoints

**Tasks:**
1. Implement login endpoint with cookie-based sessions
2. Create registration endpoint (invite-only for small team)
3. Add logout endpoint with session cleanup
4. Create password reset functionality

**Deliverables:**

`backend/app/routers/auth.py` (≤300 lines)
```python
# POST /api/auth/register - Create new user
# POST /api/auth/login - Authenticate and create session
# POST /api/auth/logout - Invalidate session
# GET /api/auth/me - Get current user
# POST /api/auth/reset-password - Reset password
```

`backend/app/auth/dependencies.py` (≤100 lines)
```python
# Update existing dependencies with real implementations
# get_current_user_required
# get_current_user_optional
# verify_api_key (for future LLM integration)
```

### Day 5: Testing & Security Hardening

**Tasks:**
1. Write comprehensive auth tests
2. Add rate limiting to auth endpoints
3. Implement CSRF protection
4. Add security headers middleware

**Deliverables:**

`backend/tests/test_auth.py` (≤400 lines)
```python
# Test user registration
# Test login/logout flow
# Test protected endpoints
# Test password reset
# Test invalid credentials
```

`backend/app/middleware/security.py` (≤150 lines)
```python
# Rate limiting middleware
# Security headers
# CSRF token validation
```

---

## Week 2: Frontend Authentication (Days 6-10)

### Day 6-7: Frontend Auth Infrastructure

**Tasks:**
1. Create auth context and hooks
2. Implement API client with auth interceptors
3. Add secure token storage
4. Create protected route wrapper

**Deliverables:**

`frontend/src/contexts/AuthContext.jsx` (≤200 lines)
```jsx
// Auth context provider
// Login/logout methods
// User state management
// Token refresh logic
```

`frontend/src/hooks/useAuth.js` (≤100 lines)
```jsx
// useAuth hook
// useRequireAuth hook
// useUser hook
```

`frontend/src/api/client.js` (≤150 lines)
```javascript
// Axios instance with interceptors
// Automatic token attachment
// Error handling for 401s
// Request retry logic
```

### Day 8-9: Authentication UI Components

**Tasks:**
1. Create login page with form validation
2. Build user profile management
3. Add navigation with auth state
4. Implement logout functionality

**Deliverables:**

`frontend/src/pages/LoginPage.jsx` (≤250 lines)
```jsx
// Login form with validation
// Remember me option
// Error handling
// Redirect after login
```

`frontend/src/components/auth/UserMenu.jsx` (≤150 lines)
```jsx
// User dropdown menu
// Profile link
// Logout button
// User info display
```

`frontend/src/components/common/ProtectedRoute.jsx` (≤100 lines)
```jsx
// Route wrapper for auth
// Redirect to login
// Loading state
```

### Day 10: Integration & Polish

**Tasks:**
1. Integrate auth across all components
2. Add loading states and error handling
3. Implement session persistence
4. Final testing and bug fixes

**Deliverables:**

`frontend/src/App.jsx` (Update ≤300 lines)
```jsx
// Add AuthProvider wrapper
// Update routing with protection
// Add global auth state handling
```

`frontend/src/stores/authStore.js` (≤150 lines)
```javascript
// Zustand store for auth state
// Persist user preferences
// Session management
```

---

## Database Migrations

`backend/alembic/versions/001_add_user_sessions.py`
```python
# Add sessions table for JWT tracking
# Add password_reset_token to users
# Add last_login timestamp
```

---

## Configuration Updates

`.env.example` additions:
```env
# Security
JWT_SECRET_KEY=generate-with-secrets-module
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Registration
REGISTRATION_ENABLED=true
INVITE_CODES=code1,code2,code3  # For small team
```

---

## Testing Plan

### Backend Tests
- User registration with valid/invalid data
- Login with correct/incorrect credentials
- Protected endpoint access
- Token expiration handling
- Password reset flow

### Frontend Tests
- Login form validation
- Protected route redirection
- Auth state persistence
- Logout functionality
- Error message display

### Integration Tests
- Full login/logout flow
- Session persistence across refreshes
- API error handling
- Concurrent session management

---

## Security Checklist

- [x] Passwords hashed with bcrypt (cost factor 12)
- [x] JWT tokens with short expiration (24h)
- [x] HttpOnly cookies for tokens
- [x] CSRF protection on state-changing operations
- [x] Rate limiting on auth endpoints (5 attempts/minute)
- [x] Secure headers (HSTS, X-Frame-Options, etc.)
- [x] Input validation on all endpoints
- [x] SQL injection protection via ORM

---

## Simplified Approach for Small Team

Since this is for 2-3 users, we're implementing:

1. **Invite-only registration** - No public signup
2. **Simple role system** - All users have equal access
3. **Shared API keys** - Managed at application level
4. **Basic password reset** - Via predefined security questions
5. **Session management** - Single session per user

---

## Dependencies to Add

`backend/requirements.txt` additions:
```
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
slowapi==0.1.9  # Rate limiting
```

`frontend/package.json` additions:
```json
"axios": "^1.6.5",
"react-router-dom": "^6.21.1",
"zustand": "^4.4.7",
"react-hook-form": "^7.48.2"
```

---

## Success Criteria

1. Users can register with invite code
2. Users can login and receive JWT token
3. Protected routes redirect to login
4. Sessions persist across page refreshes
5. Logout clears all auth state
6. Password reset works via email
7. All auth endpoints have tests
8. No modules exceed 900 lines

---

## Next Phase Preview

Phase 3 will build upon authentication to implement:
- Project CRUD operations with ownership
- Multi-project support
- Timeline event tracking
- Basic file upload functionality

This keeps the implementation focused and avoids over-engineering while providing a solid foundation for the remaining features.
