# Remediation Plan for Known Issues

This document outlines **concrete engineering tasks** to fix the five
problem areas uncovered during the recent audit (file uploads, chat
manager, project context, code-editing, and LLM errors).

---

## 1. File-Upload Pipeline

| Objective | Detailed steps & design notes |
|-----------|--------------------------------|
| **Memory & size limits** | 1. Add new fields to `app.config.Settings`:<br>   ```python
   max_upload_size_mb: int = 10
   max_upload_total_mb: int = 50
   ```<br>   2. Validate in `routers/code.py` **before** reading whole file:<br>      ```python
      file_size = upload.spool_max_size or (await upload.read(...))
      if file_size > settings.max_upload_size_mb * 1_048_576:
          raise HTTPException(413, "File too large")
      total += file_size
      ```<br>   3. Return RFC-9110 payload-too-large response JSON `{detail:"file too large", limit:10}`. |
| **Background-task session** | 1. Change signature to `_process_code_file(doc_id:int, content:str, language:str)`.<br>   2. Remove `db` arg in `background_tasks.add_task` call.<br>   3. Inside `_process_code_file` open its own `SessionLocal()` (already present). |
| **Embedding index flag** | 1. Add column `needs_embedding` (Boolean, default **True**) via Alembic revision:<br>   ```python
   op.add_column('code_documents', sa.Column('needs_embedding', sa.Boolean(), server_default='1'))
   op.execute('UPDATE code_documents SET needs_embedding = 0 WHERE is_indexed = 1')
   op.drop_column('code_documents', 'is_indexed')
   ```<br>   2. In `_process_code_file` set `doc.needs_embedding = False` after `session.commit()`. |
| **Duplicate / update logic** | 1. Calculate `content_hash` with `hashlib.sha256` **before** DB insert.<br>   2. Query by `(project_id, file_path)`.<br>      • If not found → insert.<br>      • If found and `content_hash` identical → respond `{status:"duplicate"}`.<br>      • If found and **different** →
        a. delete old embeddings (`session.query(CodeEmbedding).filter_by(document_id=doc.id).delete()`)
        b. update size, hash, language, timestamps, set `needs_embedding=True`.<br>      • Commit and enqueue background re-parse. |
| **Tests** | • Parametrised pytest using `UploadFile` fixture.<br>  • Use SQLite in-memory DB.<br>  • Verify 413 on oversize, duplicate recognition, update path resets flag. |

---

## 2. Chat Manager & WebSocket Layer

| Objective | Detailed steps & design notes |
|-----------|--------------------------------|
| **Thread-safety** | 1. Replace `Dict[int, List[WebSocket]]` with `Dict[int, Set[WebSocket]]`.<br>   2. Wrap mutating blocks in `async with self._lock:`.<br>   3. Iterate over `set(active)` copy when broadcasting to avoid mutation during iteration. |
| **Disconnect handling** | 1. In `send_message()` catch `RuntimeError`, `WebSocketDisconnect`, `Exception`.<br>   2. Move disconnect cleanup to single place: `await self._safe_disconnect(ws, …)` which handles `discard`. |
| **Authorisation** | 1. New helper in `chat_service.py`:<br>   ```python
   def session_accessible(db, session_id, user_id):
       return db.scalar(select(ChatSession).join(Project).filter(ChatSession.id==session_id, Project.owner_id==user_id)) is not None
   ```<br>   2. Call before WS accept and in REST routers. |
| **Broadcast payload** | 1. Build a serializer `serialize_message()` **once** and use for `new_message`, `message_updated`.<br>   2. Clients receive full object and patch by `id`. |
| **Tests** | • Use FastAPI `TestClient` + `websockets` lib.<br>  • Scenario: user-A cannot connect to user-B’s session (403).<br>  • Broadcast message arrives to two sockets, no duplication after one socket closes early. |

---

## 3. Project Context & Timeline

| Objective | Detailed steps & design notes |
|-----------|--------------------------------|
| **Ownership rules** | 1. Change `can_modify()` to `return self.owner_id == user_id`.<br>   2. Routers: `upload_code_files`, `update_project`, `delete_project`, etc. call `project.can_modify(current_user.id)` and raise 403 if false. |
| **Timeline coverage** | 1. Add helper `add_timeline_event(project_id, event_type, title, metadata={})` in `services.timeline`. 2. Hook points:<br>   • after successful file upload.<br>   • after `ProjectUpdate` if any field changes (store diff in metadata).<br>   • after status transition (event_type `status_changed`).<br>   • on project delete (event_type `project_deleted`). |
| **Stats helper** | Move private `_get_project_stats` to public `get_project_stats` in `ProjectService` and mark as cached property where feasible. |
| **Tests** | • Ensure non-owner PATCH returns 403.<br>  • After status change `/api/timeline` returns latest event with correct metadata. |

---

## 4. Code Editing / Update Functionality

| Objective | Detailed steps & design notes |
|-----------|--------------------------------|
| **Edit endpoint** | 1. New Pydantic schema `CodeUpdate { content:str, version:int }`.<br>   2. Route: `@router.put("/files/{file_id}")` ↦ checks ownership + locking, then reuses `parse_chunk_and_save()` helper (extracted from upload logic). |
| **Optimistic locking** | 1. Alembic: `version INT NOT NULL DEFAULT 1`.<br>   2. When updating: `if payload.version != doc.version: raise 409`.<br>   3. On success: increment `doc.version += 1`. |
| **Regex robustness** | Replace in `ChatProcessor._extract_code_snippets` with:<br>   ```python
   pattern = re.compile(r'```(?:([^\n]+)\n)?([\s\S]+?)```')
   ``` |
| **History** | New table `code_document_versions` (id, document_id, content_hash, created_at).  Trigger insert **before** update to keep one row per previous version. |
| **Tests** | • 409 on stale version.<br>  • Editing updates `version`, re-parses language.<br>  • Snippet regex passes nested back-tick test. |

---

## 5. LLM Interaction / 403 `model_not_found`

| Objective | Detailed steps & design notes |
|-----------|--------------------------------|
| **Configurable model** | 1. In `config.py` add `llm_default_model: str = "gpt-3.5-turbo"` and deprecate `llm_model`.<br>   2. Read env `LLM_MODEL` to override.  Update docs. |
| **Automatic fallback** | 1. Modify `LLMClient.__init__` to hold `self.active_model = settings.llm_default_model`.<br>   2. Wrap API call: on `openai.APIError` or `httpx.HTTPStatusError` with `model_not_found`, set `self.active_model = 'gpt-3.5-turbo'` then retry **once**.<br>   3. Persist chosen model in-memory until process restart. |
| **User-friendly error** | 1. `ChatProcessor._generate_ai_response` catches raised error and pushes `{'type':'error','message':'LLM currently unavailable. Please try again.'}`.
   2. Write log at ERROR level with full stack for operators. |
| **Tests** | • Use `unittest.mock.patch('openai.AsyncOpenAI.chat.completions.create')` to raise 403 on first call.<br>  • Verify second call made with fallback model.<br>  • Verify WebSocket receives friendly error when fallback also fails. |

---

## Execution Order

1. **LLM fallback** – unblocks chat functionality.
2. **Chat manager hardening** – stabilise real-time comms.
3. **File-upload improvements** – memory safety & correct flags.
4. **Project ownership & timeline** – security + activity feed.
5. **Code edit endpoint** – completes CRUD cycle after preceding fixes.

Each milestone ships with Alembic migration (if schema changes) and new
pytest coverage. CI runs `make test && make lint` on every PR.

---

*Last updated: 2025-06-09*
