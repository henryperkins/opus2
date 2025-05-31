# Project Management API

## GET /api/projects

List (with filter/search/pagination):

Request:
`GET /api/projects?status=active&tags=phase3,ai&search=dashboard`

Response:
```json
{
  "items": [
    {
      "id": 1,
      "title": "AI Productivity App",
      "description": "Phase 3 implementation",
      "status": "active",
      "color": "#3B82F6",
      "emoji": "🚀",
      "tags": ["phase3", "ai"],
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

## POST /api/projects

Create:
```json
{
  "title": "New Project",
  "description": "Project description",
  "status": "active",
  "color": "#10B981",
  "emoji": "💡",
  "tags": ["research", "ai"]
}
```

## GET /api/projects/{id}
Details for a project (owner, timeline id refs, etc).

## PUT /api/projects/{id}

Update one or more project fields.

## DELETE /api/projects/{id}

Remove a project (cascade deletes timeline).

## GET /api/projects/{id}/timeline

List all timeline events for a project.

## POST /api/projects/{id}/timeline

Add new timeline event (event_type/title/description/metadata).

All endpoints require authentication.  Pagination and status/tag/searching supported for `/api/projects`.

---
