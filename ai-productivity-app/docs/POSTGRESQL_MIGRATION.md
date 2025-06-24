# PostgreSQL Migration Guide

This guide covers migrating the AI Productivity App from SQLite to PostgreSQL for improved performance, scalability, and advanced features.

## Why PostgreSQL?

**Performance Benefits:**
- Better concurrent user support
- Advanced indexing (GIN, GiST, partial indexes)
- Connection pooling and query optimization
- Full-text search with ranking

**Advanced Features:**
- JSONB for efficient JSON operations
- Vector similarity search (with pgvector)
- Advanced text search with stemming
- Trigram similarity matching
- Rich SQL functions and aggregations

## Migration Steps

### 1. Environment Setup

Update your `.env` file:
```bash
# PostgreSQL Configuration
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/ai_productivity"

# Optional: Vector store configuration
VECTOR_STORE_TYPE="sqlite_vss"  # Keep sqlite_vss or switch to qdrant

# PostgreSQL Docker settings (for docker-compose)
POSTGRES_DB="ai_productivity"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"
```

### 2. Docker Compose Setup

The docker-compose.yml has been updated to include PostgreSQL:

```bash
# Start the stack with PostgreSQL
make dev

# Or manually:
docker-compose up -d postgres
docker-compose up backend frontend
```

**PostgreSQL Service Features:**
- PostgreSQL 15 Alpine image
- Persistent data volume
- Health checks
- Custom initialization script with extensions

### 3. Database Migration

**Run Alembic migrations:**
```bash
cd backend
alembic upgrade head
```

**The migration includes:**
- All existing tables and relationships
- PostgreSQL-specific indexes for performance
- Full-text search indexes
- JSON/JSONB indexes for metadata
- Partial indexes for active records

### 4. Data Migration (if needed)

**From existing SQLite database:**
```bash
# Export data from SQLite (if you have existing data)
python backend/scripts/export_sqlite_data.py

# Import to PostgreSQL
python backend/scripts/import_to_postgres.py
```

## PostgreSQL-Specific Features

### 1. Enhanced Full-Text Search

**Before (SQLite FTS5):**
```sql
SELECT * FROM content_fts WHERE content_fts MATCH 'search term'
```

**After (PostgreSQL FTS):**
```sql
SELECT *, ts_rank(to_tsvector('ai_english', content), plainto_tsquery('ai_english', 'search term')) as rank
FROM documents 
WHERE to_tsvector('ai_english', content) @@ plainto_tsquery('ai_english', 'search term')
ORDER BY rank DESC
```

### 2. Advanced JSON Operations

**JSONB Indexing:**
```sql
-- Fast JSON queries
SELECT * FROM projects WHERE tags @> '["python"]'
SELECT * FROM projects WHERE tags ? 'react'
```

**JSON Aggregations:**
```sql
-- Aggregate project languages
SELECT project_id, json_agg(DISTINCT language) as languages
FROM code_documents 
GROUP BY project_id
```

### 3. Vector Search (Future)

With pgvector extension:
```sql
-- Vector similarity search
SELECT *, embedding <=> query_vector as distance
FROM code_embeddings 
ORDER BY embedding <=> query_vector 
LIMIT 10
```

## Performance Optimizations

### 1. Indexes Created

**Full-Text Search:**
- `idx_projects_fts` - Projects title/description search
- `idx_chat_messages_fts` - Chat message content search
- `idx_code_documents_fts` - Code file path search

**JSON Indexes:**
- `idx_projects_tags_gin` - Project tags
- `idx_chat_messages_metadata_gin` - Chat metadata
- `idx_code_documents_symbols_gin` - Code symbols

**Composite Indexes:**
- `idx_chat_messages_session_active` - Active messages per session
- `idx_code_documents_project_lang` - Documents by project and language
- `idx_timeline_events_project_type` - Timeline events by project and type

**Partial Indexes:**
- `idx_projects_active` - Non-archived projects only
- `idx_chat_sessions_active` - Active chat sessions only

**Trigram Indexes:**
- `idx_projects_title_trgm` - Fuzzy title search
- `idx_code_documents_path_trgm` - Fuzzy file path search

### 2. Query Performance

**Connection Pooling:**
- SQLAlchemy pool size: 20 connections
- Pool overflow: 30 additional connections
- Connection recycling: 3600 seconds

**Query Optimization:**
- Prepared statements for repeated queries
- EXPLAIN ANALYZE for slow query identification
- Index usage monitoring

## Configuration Options

### 1. Database URLs

**Local Development:**
```
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/ai_productivity"
```

**Docker Compose:**
```
DATABASE_URL="postgresql://postgres:postgres@postgres:5432/ai_productivity"
```

**Production (example):**
```
DATABASE_URL="postgresql://username:password@db.example.com:5432/ai_productivity"
```

### 2. Connection Settings

```python
# In app/config.py - SQLAlchemy engine configuration
engine = create_engine(
    database_url,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    pool_pre_ping=True
)
```

## Monitoring and Maintenance

### 1. Query Performance

**Monitor slow queries:**
```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();

-- Check slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

### 2. Database Maintenance

**Regular maintenance tasks:**
```bash
# Vacuum and analyze
psql -d ai_productivity -c "VACUUM ANALYZE;"

# Reindex (if needed)
psql -d ai_productivity -c "REINDEX DATABASE ai_productivity;"

# Check database size
psql -d ai_productivity -c "SELECT pg_size_pretty(pg_database_size('ai_productivity'));"
```

## Troubleshooting

### 1. Connection Issues

**Check PostgreSQL status:**
```bash
docker-compose exec postgres pg_isready -U postgres
```

**View logs:**
```bash
docker-compose logs postgres
docker-compose logs backend
```

### 2. Migration Issues

**Reset database (development only):**
```bash
docker-compose down
docker volume rm ai-productivity-app_postgres_data
docker-compose up -d postgres
cd backend && alembic upgrade head
```

**Check migration status:**
```bash
cd backend
alembic current
alembic history
```

### 3. Performance Issues

**Check index usage:**
```sql
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
```

**Monitor connection count:**
```sql
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';
```

## Rollback Strategy

To rollback to SQLite (emergency only):

1. Update `.env`:
   ```
   DATABASE_URL="sqlite:///data/app.db"
   ```

2. Restart services:
   ```bash
   docker-compose restart backend
   ```

3. Run SQLite migrations:
   ```bash
   cd backend
   alembic upgrade head
   ```

## Next Steps

1. **Monitor Performance**: Use pg_stat_statements and query logs
2. **Optimize Queries**: Add indexes based on actual usage patterns  
3. **Vector Search**: Consider migrating to pgvector for vector operations
4. **Read Replicas**: Set up read replicas for analytics queries
5. **Backup Strategy**: Implement automated PostgreSQL backups

## Support

For issues with PostgreSQL migration:
1. Check the troubleshooting section above
2. Review Docker Compose logs
3. Verify environment configuration
4. Test with a fresh database

The migration maintains full backward compatibility with existing features while unlocking PostgreSQL's advanced capabilities for better performance and scalability.