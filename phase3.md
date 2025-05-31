# Phase 3 Implementation Plan: Project Management System

## Overview

Phase 3 implements the core project management functionality, building on the authentication foundation from Phase 2. This phase focuses on practical project organization features for a small team without over-engineering.

## Timeline: 2 Weeks (10 Business Days)

## Objectives

1. Implement full CRUD operations for projects
2. Add project status tracking and metadata
3. Create timeline event system for project history
4. Build intuitive project dashboard UI

## Technical Approach

- **Backend**: RESTful APIs with SQLAlchemy models
- **Frontend**: React components with Zustand state management
- **Database**: SQLite with proper relationships
- **Architecture**: Simple, direct implementation avoiding complexity

---

## Week 1: Backend Project Management (Days 1-5)

### Day 1-2: Database Models & Schemas

**Tasks:**

1. Enhance existing Project model with full features
2. Create TimelineEvent model for project history
3. Add database relationships and constraints
4. Create Pydantic schemas for validation

**Deliverables:**

`backend/app/models/project.py` (Update ≤250 lines)

```python
# Enhanced Project model with:
# - Status enum (Active, Archived, Completed)
# - Color and emoji fields
# - Tags as JSON field
# - Relationship to timeline events
# - Proper indexes for performance
```

`backend/app/models/timeline.py` (≤150 lines)

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin

class TimelineEvent(Base, TimestampMixin):
    __tablename__ = 'timeline_events'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    event_type = Column(String(50), nullable=False)  # created, updated, file_added, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text)
    metadata = Column(JSON)  # Flexible data storage

    # Relationships
    project = relationship("Project", back_populates="timeline_events")
```

`backend/app/schemas/project.py` (≤200 lines)

```python
# ProjectCreate - for new projects
# ProjectUpdate - for modifications
# ProjectResponse - with all fields
# ProjectListResponse - optimized list view
# TimelineEventResponse - for history
```

### Day 3-4: Project CRUD Endpoints

**Tasks:**

1. Implement project CRUD operations
2. Add timeline event tracking
3. Create project filtering and search
4. Add proper authorization checks

**Deliverables:**

`backend/app/routers/projects.py` (≤400 lines)

```python
# GET /api/projects - List all projects with filters
# POST /api/projects - Create new project
# GET /api/projects/{id} - Get project details
# PUT /api/projects/{id} - Update project
# DELETE /api/projects/{id} - Delete project
# GET /api/projects/{id}/timeline - Get project timeline
# POST /api/projects/{id}/timeline - Add timeline event
```

`backend/app/services/project_service.py` (≤200 lines)

```python
# Business logic layer:
# - create_project_with_timeline
# - update_project_status
# - archive_project
# - add_timeline_event
# - get_projects_with_stats
```

### Day 5: Testing & Validation

**Tasks:**

1. Write comprehensive project tests
2. Add input validation
3. Test timeline event creation
4. Verify authorization logic

**Deliverables:**

`backend/tests/test_projects.py` (≤400 lines)

```python
# Test project CRUD operations
# Test status transitions
# Test timeline events
# Test authorization
# Test filtering and search
```

`backend/alembic/versions/002_add_project_features.py`

```python
# Add color and emoji columns
# Add tags JSON column
# Create timeline_events table
# Add proper indexes
```

---

## Week 2: Frontend Project Management (Days 6-10)

### Day 6-7: Project State Management & API

**Tasks:**

1. Create project store with Zustand
2. Implement API client for projects
3. Add caching and optimistic updates
4. Handle loading and error states

**Deliverables:**

`frontend/src/stores/projectStore.js` (≤250 lines)

```javascript
import { create } from 'zustand';
import { projectAPI } from '../api/projects';

const useProjectStore = create((set, get) => ({
  projects: [],
  currentProject: null,
  loading: false,
  error: null,

  // Actions
  fetchProjects: async (filters) => {
    set({ loading: true });
    try {
      const projects = await projectAPI.list(filters);
      set({ projects, loading: false });
    } catch (error) {
      set({ error: error.message, loading: false });
    }
  },

  createProject: async (data) => {
    // Optimistic update
    const tempProject = { ...data, id: Date.now(), status: 'active' };
    set(state => ({ projects: [...state.projects, tempProject] }));

    try {
      const project = await projectAPI.create(data);
      set(state => ({
        projects: state.projects.map(p =>
          p.id === tempProject.id ? project : p
        )
      }));
      return project;
    } catch (error) {
      // Rollback on error
      set(state => ({
        projects: state.projects.filter(p => p.id !== tempProject.id),
        error: error.message
      }));
      throw error;
    }
  },

  // ... other actions
}));
```

`frontend/src/api/projects.js` (≤150 lines)

```javascript
import client from './client';

export const projectAPI = {
  list: (filters = {}) =>
    client.get('/api/projects', { params: filters }).then(r => r.data),

  get: (id) =>
    client.get(`/api/projects/${id}`).then(r => r.data),

  create: (data) =>
    client.post('/api/projects', data).then(r => r.data),

  update: (id, data) =>
    client.put(`/api/projects/${id}`, data).then(r => r.data),

  delete: (id) =>
    client.delete(`/api/projects/${id}`),

  getTimeline: (id) =>
    client.get(`/api/projects/${id}/timeline`).then(r => r.data)
};
```

### Day 8-9: Project UI Components

**Tasks:**

1. Create project dashboard layout
2. Build project cards with status badges
3. Implement create/edit project modal
4. Add timeline visualization

**Deliverables:**

`frontend/src/pages/ProjectsPage.jsx` (≤300 lines)

```jsx
import { useEffect } from 'react';
import { useProjectStore } from '../stores/projectStore';
import ProjectCard from '../components/projects/ProjectCard';
import CreateProjectModal from '../components/projects/CreateProjectModal';

export default function ProjectsPage() {
  const { projects, loading, fetchProjects } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, []);

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Projects</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn btn-primary"
        >
          New Project
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map(project => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </div>
  );
}
```

`frontend/src/components/projects/ProjectCard.jsx` (≤200 lines)

```jsx
// Visual project card with:
// - Status badge (color-coded)
// - Emoji and title
// - Description preview
// - Tags display
// - Quick actions (edit, archive, delete)
// - Last activity timestamp
```

`frontend/src/components/projects/CreateProjectModal.jsx` (≤250 lines)

```jsx
// Modal form with:
// - Title and description inputs
// - Status selector
// - Color picker
// - Emoji picker
// - Tag input with autocomplete
// - Form validation
// - Loading states
```

`frontend/src/components/projects/Timeline.jsx` (≤200 lines)

```jsx
// Timeline visualization showing:
// - Chronological event list
// - Event type icons
// - Relative timestamps
// - Event details on hover
// - Filter by event type
```

### Day 10: Integration & Polish

**Tasks:**

1. Integrate project management with navigation
2. Add search and filtering UI
3. Implement keyboard shortcuts
4. Final testing and bug fixes

**Deliverables:**

`frontend/src/components/projects/ProjectFilters.jsx` (≤150 lines)

```jsx
// Filter controls for:
// - Status (Active, Archived, Completed)
// - Tags
// - Date range
// - Search by title
```

`frontend/src/hooks/useProjects.js` (≤100 lines)

```javascript
// Custom hooks for common project operations
// - useProject(id) - single project with caching
// - useProjectTimeline(id) - timeline events
// - useProjectSearch() - search functionality
```

---

## API Endpoint Specifications

### Project Endpoints

**GET /api/projects**

```json
Query params: ?status=active&tags=backend,frontend&search=ai
Response: {
  "items": [
    {
      "id": 1,
      "title": "AI Productivity App",
      "description": "Main development project",
      "status": "active",
      "color": "#3B82F6",
      "emoji": "🚀",
      "tags": ["backend", "frontend"],
      "owner": { "id": 1, "username": "admin" },
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T00:00:00Z",
      "stats": {
        "files": 42,
        "timeline_events": 15,
        "last_activity": "2024-01-15T00:00:00Z"
      }
    }
  ],
  "total": 10,
  "page": 1,
  "per_page": 20
}
```

**POST /api/projects**

```json
Request: {
  "title": "New Project",
  "description": "Project description",
  "status": "active",
  "color": "#10B981",
  "emoji": "💡",
  "tags": ["research", "ai"]
}
Response: { ...created project... }
```

---

## Component Structure

```
frontend/src/
├── pages/
│   ├── ProjectsPage.jsx          # Main projects dashboard
│   └── ProjectDetailPage.jsx     # Individual project view
├── components/
│   └── projects/
│       ├── ProjectCard.jsx       # Project card component
│       ├── ProjectForm.jsx       # Reusable form for create/edit
│       ├── CreateProjectModal.jsx # Modal wrapper for creation
│       ├── EditProjectModal.jsx  # Modal wrapper for editing
│       ├── ProjectFilters.jsx    # Filter controls
│       ├── ProjectStatus.jsx     # Status badge component
│       ├── Timeline.jsx          # Timeline visualization
│       └── TimelineEvent.jsx     # Individual timeline item
├── stores/
│   └── projectStore.js          # Zustand store for projects
├── api/
│   └── projects.js              # Project API client
└── hooks/
    └── useProjects.js           # Custom project hooks
```

---

## Styling Approach

Using Tailwind CSS utility classes with custom components:

```css
/* Project status badges */
.badge-active { @apply bg-green-100 text-green-800; }
.badge-archived { @apply bg-gray-100 text-gray-800; }
.badge-completed { @apply bg-blue-100 text-blue-800; }

/* Project cards */
.project-card {
  @apply bg-white rounded-lg shadow-md p-6
         hover:shadow-lg transition-shadow cursor-pointer;
}

/* Timeline styles */
.timeline-event {
  @apply relative pl-8 pb-8
         before:absolute before:left-0 before:top-0
         before:h-full before:w-0.5 before:bg-gray-300;
}
```

---

## Testing Plan

### Backend Tests

- Project CRUD with valid/invalid data
- Status transition rules
- Timeline event creation
- Tag management
- Search and filtering
- Authorization checks

### Frontend Tests

- Project card rendering
- Form validation
- Optimistic updates
- Error handling
- Timeline visualization
- Filter interactions

---

## Migration Scripts

`backend/scripts/migrate_projects.py` (≤100 lines)

```python
# One-time migration to add new fields to existing projects
# - Set default colors based on project ID
# - Assign emoji based on project type
# - Create initial timeline events
```

---

## Success Criteria

1. ✅ Users can create, read, update, delete projects
2. ✅ Projects have visual distinction (color, emoji)
3. ✅ Status transitions work correctly
4. ✅ Timeline shows project history
5. ✅ Search and filtering work efficiently
6. ✅ UI is responsive and intuitive
7. ✅ All endpoints have tests
8. ✅ No modules exceed 900 lines

---

## Performance Considerations

1. **Pagination**: Implement for project lists
2. **Caching**: Cache project data in Zustand
3. **Optimistic Updates**: Immediate UI feedback
4. **Lazy Loading**: Load timeline events on demand
5. **Database Indexes**: On foreign keys and search fields

---

## Next Phase Preview

Phase 4 will add code processing capabilities:

- File upload and parsing
- Tree-sitter integration
- Code chunking for embeddings
- Git repository integration
- Syntax highlighting

This implementation provides a solid project management foundation while maintaining simplicity and avoiding over-engineering for our small team use case.
