# PostgreSQL + pgvector Migration Guide

This document guides you through the complete migration to PostgreSQL + pgvector as the sole vector storage backend, eliminating all SQLite VSS and Qdrant dependencies.

## 🎯 Migration Overview

The RAG system has been migrated from a complex multi-backend architecture to a simplified PostgreSQL + pgvector only solution. This eliminates:

- ❌ SQLite VSS (deprecated, incomplete implementation)
- ❌ Qdrant (complex setup, external dependency)
- ✅ PostgreSQL + pgvector (reliable, integrated, scalable)

## 📋 Prerequisites

### 1. PostgreSQL with pgvector Extension

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql-15-pgvector
```

**macOS (Homebrew):**
```bash
brew install pgvector
```

**Docker:**
```bash
# Use the official pgvector image
docker run -d \
  --name pgvector \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=vectordb \
  -p 5432:5432 \
  ankane/pgvector
```

### 2. Python Dependencies

Update your `requirements.txt`:
```
psycopg[binary]~=3.1
pgvector~=0.2
sqlalchemy~=2.0
# Remove: aiosqlite, qdrant-client
```

## 🔧 Configuration Changes

### Environment Variables

Update your `.env` file:
```bash
# Vector Store Configuration
VECTOR_STORE_TYPE=pgvector  # Only supported value

# PostgreSQL Configuration
POSTGRES_URL=postgresql+psycopg://user:password@localhost:5432/vectordb
POSTGRES_VECTOR_TABLE=embeddings
EMBEDDING_VECTOR_SIZE=1536

# Remove these deprecated variables:
# SQLITE_VSS_PATH=...
# QDRANT_URL=...
# QDRANT_API_KEY=...
```

### Application Configuration

The system now enforces pgvector-only operation. Any attempt to use other backends will raise a configuration error:

```python
# This will now raise a ValueError
VECTOR_STORE_TYPE=sqlite_vss  # ❌ Not supported
VECTOR_STORE_TYPE=qdrant      # ❌ Not supported
VECTOR_STORE_TYPE=pgvector    # ✅ Only supported option
```

## 🗄️ Database Migration

### 1. Run the Migration

```bash
cd backend
alembic upgrade head
```

This will:
- Enable the pgvector extension
- Create the `code_embedding_vectors` table
- Create the `knowledge_embedding_vectors` table
- Add appropriate indexes for vector similarity search

### 2. Verify Installation

```sql
-- Connect to your database
psql -d vectordb

-- Verify pgvector is installed
\dx pgvector

-- Check tables exist
\dt *embedding*

-- Verify vector columns
\d code_embedding_vectors
\d knowledge_embedding_vectors
```

## 🚀 Application Changes

### Simplified Architecture

The new architecture is much cleaner:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   VectorService │───▶│ PostgresVector   │───▶│ PostgreSQL +    │
│                 │    │ Service          │    │ pgvector        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Before (Complex):**
- Multiple backend adapters
- Conditional logic based on `vector_store_type`
- Different APIs for different backends
- Silent fallbacks and degraded modes

**After (Simple):**
- Single backend: PostgreSQL + pgvector
- No conditional logic
- Unified API
- Fail-fast configuration validation

### Code Changes Summary

**Removed Files:**
- `app/services/vector_store.py` (SQLite VSS stub)
- `app/services/vector_service_old.py` (complex multi-backend service)

**Simplified Files:**
- `app/services/vector_service.py` - Now pgvector-only
- `app/config.py` - Validates pgvector-only configuration
- `app/services/hybrid_search.py` - Uses VectorService directly
- `app/routers/search.py` - No more VectorStore stub

**New Files:**
- `app/utils/token_counter.py` - Unified token counting
- `alembic/versions/migrate_to_pgvector_only.py` - Database migration

## 🧪 Testing

### Unit Tests

Update your test configuration to use pgvector:

```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container with pgvector for tests."""
    with PostgresContainer(
        "ankane/pgvector:latest",
        dbname="test_vectordb",
        username="test",
        password="test"
    ) as postgres:
        yield postgres

@pytest.fixture
def test_db_url(postgres_container):
    """Get test database URL."""
    return postgres_container.get_connection_url()
```

### Integration Tests

Test the full RAG pipeline:

```python
async def test_vector_operations():
    """Test complete vector operations with pgvector."""
    vector_service = VectorService()
    await vector_service.initialize()
    
    # Test embedding insertion
    embeddings = [
        {
            "id": 1,
            "vector": [0.1] * 1536,
            "content": "test content",
            "document_id": 1,
            "project_id": 1,
        }
    ]
    ids = await vector_service.insert_embeddings(embeddings)
    assert len(ids) == 1
    
    # Test vector search
    results = await vector_service.search(
        query_vector=np.array([0.1] * 1536),
        limit=10
    )
    assert len(results) >= 1
```

## 📊 Performance Considerations

### Vector Indexes

The migration creates IVFFlat indexes by default:

```sql
-- Good for datasets < 1M vectors
CREATE INDEX idx_code_emb_vector_ivfflat
ON code_embedding_vectors
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

For larger datasets (> 1M vectors), consider HNSW:

```sql
-- Better for large datasets
CREATE INDEX idx_code_emb_vector_hnsw
ON code_embedding_vectors
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);
```

### Performance Tuning

1. **Analyze Statistics:**
   ```sql
   ANALYZE code_embedding_vectors;
   ANALYZE knowledge_embedding_vectors;
   ```

2. **Adjust Lists Parameter:**
   ```sql
   -- For datasets with 100K-1M vectors
   DROP INDEX idx_code_emb_vector_ivfflat;
   CREATE INDEX idx_code_emb_vector_ivfflat
   ON code_embedding_vectors
   USING ivfflat (embedding vector_cosine_ops)
   WITH (lists = 200);
   ```

3. **Memory Settings:**
   ```sql
   -- PostgreSQL configuration
   shared_buffers = 256MB          -- Adjust based on available RAM
   work_mem = 64MB                 -- For large vector operations
   maintenance_work_mem = 256MB    -- For index creation
   ```

## 🔍 Monitoring & Observability

### Vector Store Metrics

The simplified VectorService provides comprehensive stats:

```python
stats = await vector_service.get_stats()
# Returns:
# {
#   "backend": "pgvector",
#   "table": "embeddings", 
#   "total_embeddings": 50000,
#   "by_project": {1: 25000, 2: 25000}
# }
```

### Query Performance

Monitor slow vector queries:

```sql
-- Enable query logging in postgresql.conf
log_min_duration_statement = 1000  -- Log queries > 1s

-- Monitor vector searches
SELECT query, total_time, calls
FROM pg_stat_statements
WHERE query LIKE '%vector_cosine_ops%'
ORDER BY total_time DESC;
```

## 🚨 Troubleshooting

### Common Issues

**1. pgvector Extension Not Found**
```bash
ERROR: extension "pgvector" is not available
```
**Solution:** Install pgvector package for your PostgreSQL version.

**2. Vector Dimension Mismatch**
```bash
ERROR: dimension mismatch
```
**Solution:** Ensure `EMBEDDING_VECTOR_SIZE` matches your model's output dimension.

**3. Configuration Validation Error**
```bash
ValueError: Unsupported vector_store_type: sqlite_vss
```
**Solution:** Update `VECTOR_STORE_TYPE=pgvector` in your environment.

**4. Missing Token Counter**
```bash
ModuleNotFoundError: No module named 'app.utils.token_counter'
```
**Solution:** The unified token counter was added. Ensure your code is up to date.

### Recovery Procedures

**Rollback Migration:**
```bash
alembic downgrade -1
```

**Backup Before Migration:**
```bash
pg_dump vectordb > backup_before_migration.sql
```

**Restore if Needed:**
```bash
psql vectordb < backup_before_migration.sql
```

## ✅ Verification Checklist

After migration, verify:

- [ ] pgvector extension is enabled: `\dx pgvector`
- [ ] Vector tables exist with correct schema
- [ ] Application starts without configuration errors
- [ ] Vector insertion works: Test with sample embeddings
- [ ] Vector search returns results with proper similarity scores
- [ ] RAG pipeline works end-to-end
- [ ] Token counting is accurate and consistent
- [ ] Performance is acceptable for your dataset size

## 🎉 Benefits Realized

After completing this migration, you should see:

1. **🔒 Reliability**: No more silent RAG failures or degraded modes
2. **⚡ Performance**: True async operations, no blocking SQLite calls
3. **📊 Accuracy**: Unified token counting prevents context overruns
4. **🧹 Maintainability**: Single backend, simplified code paths
5. **📈 Scalability**: pgvector handles production workloads
6. **🛡️ Robustness**: Fail-fast configuration validation

The RAG system is now production-ready with a clean, maintainable architecture!
