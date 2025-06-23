# Example: How to use Qdrant in your AI Productivity App

This document shows how to use Qdrant vector database in your application.

## Current Setup

Your app currently uses SQLite VSS for vector storage. The existing `VectorStore` class in `backend/app/services/vector_store.py` handles:
- Embedding storage and retrieval
- Cosine similarity search
- Project-scoped searches
- Automatic fallback when VSS extensions aren't available

## Using Qdrant

### 1. Start Qdrant Service

```bash
# Option 1: Use the separate Qdrant compose file
docker-compose -f docker-compose.qdrant.yml up -d

# Option 2: Uncomment Qdrant service in main docker-compose.yml
# Then run: docker-compose up -d
```

### 2. Basic Qdrant Operations

```python
from backend.app.services.qdrant_service import QdrantService
import numpy as np

# Initialize service
qdrant = QdrantService(host="localhost", port=6333)

# Create collection if it doesn't exist
await qdrant.create_index_if_missing()

# Insert embeddings
embeddings = [{
    "id": "doc_123_chunk_1",
    "vector": np.random.rand(1536),  # OpenAI embedding
    "document_id": 123,
    "project_id": 456,
    "content": "This is a code snippet about authentication",
    "chunk_id": 1,
    "metadata": {"file_path": "auth.py", "language": "python"}
}]

await qdrant.upsert(embeddings)

# Search for similar content
query_vector = np.random.rand(1536)
results = await qdrant.search(
    query_vector=query_vector,
    limit=5,
    project_ids=[456],  # Search within specific projects
    score_threshold=0.7
)

for result in results:
    print(f"Score: {result['score']}, Content: {result['content']}")
```

### 3. Environment Configuration

Add to your `.env` file:

```bash
# Vector database configuration
VECTOR_STORE_TYPE=qdrant  # or "sqlite_vss" for current setup
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 4. Integration with Existing Code

You can modify your existing code processing pipeline to use Qdrant:

```python
# In your existing code processing
from app.services.qdrant_service import QdrantService
from app.config import settings

# Choose vector store based on configuration
if settings.vector_store_type == "qdrant":
    vector_store = QdrantService(
        host=settings.qdrant_host,
        port=settings.qdrant_port
    )
    await vector_store.create_index_if_missing()
else:
    # Use existing SQLite VSS
    from app.services.vector_store import VectorStore
    vector_store = VectorStore()
```

## Benefits of Qdrant vs SQLite VSS

### Qdrant Advantages:
- Better performance for large datasets (>100K vectors)
- Advanced filtering capabilities
- Distributed deployment support
- Better monitoring and metrics
- HNSW index optimization
- Horizontal scaling

### SQLite VSS Advantages:
- Simpler deployment (single file)
- No additional service dependencies
- Better for small to medium datasets
- Integrated with your existing SQLite database
- Automatic fallback to JSON storage

## Performance Comparison

Based on your hardening checklist target: **search < 50ms for 100K vectors**

- **SQLite VSS**: Good for <50K vectors, performance degrades with larger datasets
- **Qdrant**: Designed for 100K+ vectors, maintains <50ms search times with proper HNSW configuration

## Migration Path

If you decide to switch from SQLite VSS to Qdrant:

1. Export existing embeddings from SQLite VSS
2. Start Qdrant service
3. Migrate embeddings to Qdrant
4. Update configuration to use Qdrant
5. Test thoroughly before production deployment

## Current Status

Your app is well-architected with the existing SQLite VSS solution. Qdrant would be beneficial if you need:
- Better performance with large vector datasets
- Advanced filtering capabilities
- Distributed deployment
- Better observability and monitoring
