# Codebase Indexing with Azure OpenAI

> This document describes how to enable and operate the experimental **Codebase Indexing** feature using an Azure OpenAI embedding deployment (`text-embedding-3-small`).  The same workflow also applies to other OpenAI-compatible providers; adjust the environment variables accordingly.

## What you get

* Semantic search across every file in your projects
* Hybrid keyword + vector retrieval via `/api/search`
* Automatic de-duplication & metadata storage in SQLite-VSS (or Qdrant)

## Prerequisites

1. An active Azure OpenAI resource.
2. A **deployment** named `text-embedding-3-small` (or any supported model).
3. API key **or** Entra ID credentials with the `Cognitive Services OpenAI User` role.
4. Python ≥ 3.11, Node 18+, Docker (optional).

## Required environment variables

Copy/update the following keys in [`backend/.env`](../backend/.env.example):

```dotenv
# --- LLM / Embeddings -------------------------------------------------
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://<your-resource-name>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-api-key>         # omit when using Entra ID
AZURE_AUTH_METHOD=api_key                   # or "entra_id"
AZURE_OPENAI_API_VERSION=2025-04-01-preview
# Embedding deployment used by EmbeddingGenerator
EMBEDDING_MODEL=text-embedding-3-small
```

**Tip :** keep secrets out of Git – follow the pattern in `.env.example`.

## Data store options

| Store             | Default | When to use                                      |
|-------------------|---------|--------------------------------------------------|
| SQLite VSS        | ✔️       | Local dev / small repos (<100 MB code)           |
| Qdrant (external) |         | Distributed / >1 M vectors / multiple workers    |
| PostgreSQL + pgvector |         | Native similarity search in existing Postgres |

### Enabling pgvector on PostgreSQL

1. Install the [pgvector](https://github.com/pgvector/pgvector) extension in your cluster (>= 0.5.0):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

2. Tell the backend to use it:

```dotenv
VECTOR_STORE_TYPE=postgres
POSTGRES_VECTOR_TABLE=code_embedding_vectors   # optional override
```

When `VECTOR_STORE_TYPE=postgres` the `VectorStore` class will (if present) use SQLAlchemy to write `vector(1536)` columns and create an `ivfflat` index (see upcoming migration **008_enable_pgvector.py**).

> ⚠️ pgvector currently requires manual index re-builds when you change `embedding_dim`.

### Switching to Qdrant

Set:

```dotenv
VECTOR_STORE_TYPE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=<optional>
```

## Indexing workflow

1. **Upload** files via [`POST /api/code/projects/{project_id}/upload`] – each file is parsed, chunked and stored as `CodeDocument`/`CodeEmbedding` rows (without vectors).
2. **Queue** indexing with [`POST /api/search/index`]
   ```json
   { "document_id": 123, "async_mode": true }
   ```
   This schedules `EmbeddingService.index_document()` in a background task.
3. `EmbeddingGenerator` calls Azure OpenAI in batches of 50, then writes vectors to the configured `VectorStore`.
4. `CodeDocument.is_indexed` flips to **true** when every chunk has a vector.

### Batch indexing an entire project

Use the helper script:

```bash
python backend/scripts/index_project.py --project 42
```
*(script will iterate over all documents and show a progress bar).*

## Monitoring progress

* **SQL**         : `SELECT id,file_path,is_indexed FROM code_documents WHERE project_id=42;`
* **API**         : `GET /api/code/projects/{project_id}/files`
* **Vector stats**: `GET /api/search/stats` (to be released).

## Using the vectors

*Programmatically* you normally **don’t** query the `vector` table directly –
instead use the built-in hybrid search endpoint:

```
POST /api/search
{
  "query": "user authentication middleware",
  "project_ids": [42],
  "limit": 15,
  "search_types": ["hybrid"]   // "keyword" | "vector" | "hybrid"
}
```

Behind the scenes `HybridSearch`:

1. Generates an embedding for the query
2. Searches the configured `VectorStore` (`pgvector` / SQLite VSS / Qdrant)
3. Merges results with keyword / structural matches
4. Returns a ranked list of `SearchResult` objects (score 0-1)

You can also call the **Roo CLI/IDE** tool [`codebase_search`](https://docs.roocode.com/advanced-usage/available-tools/codebase-search) which proxies to the same API.

For **SQL enthusiasts** using pgvector:

```sql
SELECT
  cd.file_path, ce.chunk_content
FROM code_embedding_vectors AS v
JOIN code_embeddings ce ON ce.id = v.embedding_id
JOIN code_documents cd ON cd.id = ce.document_id
ORDER BY v.embedding <-> '(…)';
```

Where `<->` is the pgvector cosine-distance operator.

## Re-index / delete embeddings

* Re-index  : `POST /api/search/index` with `"async_mode": false` to run synchronously.
* Delete    : `DELETE /api/search/index/{document_id}` – removes vectors & metadata.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `CLIENT_NOT_INITIALIZED` | Missing / wrong Azure credentials | Check `AZURE_OPENAI_*` vars |
| 401 from Azure | Key revoked | Regenerate key |
| Vector search returns 0 hits | Document not indexed yet | Wait for background task or lower `vector_score_threshold` |

## FAQ

**Q : Can I use a custom dimension?**
A : Yes. Set `EMBEDDING_MODEL=<deployment>:text-embedding-3-small` and pass `dimensions=<N>` when instantiating `EmbeddingGenerator`.

**Q : How do I switch to OpenAI public API?**
A : Set `LLM_PROVIDER=openai` and populate `OPENAI_API_KEY`; remove Azure vars.

**Q : Where are vectors stored?**
A : In `data/vss.db` (SQLite) or in your Qdrant cluster when enabled.

---

*Last updated : 2025-06-26*
