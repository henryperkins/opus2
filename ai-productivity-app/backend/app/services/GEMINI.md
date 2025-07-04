## Services Layer

This directory contains the business logic for the application, organized into a set of services. Each service is responsible for a specific domain of the application, such as chat, projects, or embeddings.

### Key Services

*   **`ChatService`**: Manages chat sessions and messages.
*   **`ProjectService`**: Handles project creation, updates, and timeline events.
*   **`VectorService`**: Provides a unified interface for interacting with the vector store (`pgvector` or `qdrant`).
*   **`PostgresVectorService`**: Implements the `VectorServiceProtocol` for `pgvector`.
*   **`QdrantService`**: Implements the `VectorServiceProtocol` for `qdrant`.
*   **`EmbeddingService`**: Manages the lifecycle of embeddings, including generation and storage.
*   **`HybridSearch`**: Combines vector, keyword, and structural search to provide a unified search experience.
*   **`KeywordSearch`**: Implements keyword search using PostgreSQL FTS and SQLite FTS5.
*   **`StructuralSearch`**: Implements search for code symbols and structures.
*   **`KnowledgeService`**: Manages the knowledge base, including adding and searching for knowledge entries.
*   **`ImportService`**: Manages the process of importing code from Git repositories.
*   **`RenderingService`**: Provides a client for the external Markdown rendering service.
*   **`ConfidenceService`**: Calculates confidence scores for RAG responses.
*   **`MetricsService`**: Collects and formats Prometheus metrics.
*   **`ConfigService`**: Manages the application's dynamic configuration.
*   **`PromptService`**: Manages prompt templates.
*   **`AtomicOperations`**: Provides services for performing atomic database operations.

### Design Patterns

*   **Service Layer**: The services in this directory form a classic service layer, which encapsulates the application's business logic and separates it from the presentation layer (routers) and the data access layer (models).
*   **Dependency Injection**: The services are designed to be used with FastAPI's dependency injection system. This makes them easy to test and allows for different implementations to be swapped out at runtime (e.g., the `VectorService`).
*   **Protocol-Oriented Programming**: The `VectorService` uses a `VectorServiceProtocol` to define a common interface for all vector store implementations. This allows the application to support multiple vector stores without changing the code that uses them.
*   **Resiliency**: The services are designed to be resilient, with features like retries, circuit breakers, and graceful fallbacks. For example, the `RenderingServiceClient` will fall back to a local Markdown rendering implementation if the external rendering service is unavailable.

### Future Development

*   **Adding a new service**: To add a new service, create a new file in this directory and define a class that encapsulates the business logic for the new domain.
*   **Modifying an existing service**: When modifying an existing service, be sure to maintain the separation of concerns and to follow the existing design patterns.
*   **Adding a new vector store backend**: To add support for a new vector store, create a new service class that implements the `VectorServiceProtocol` and add it to the `vector_service` factory function in `backend/app/dependencies.py`.
