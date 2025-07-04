## About This File

This `GEMINI.md` file serves as a centralized, hierarchical context for the Gemini AI. It provides project-specific instructions, documents architectural patterns, and offers an operational guide to ensure that the AI's contributions are accurate, consistent, and aligned with the project's conventions.

### Hierarchical Context

The Gemini CLI uses a hierarchical system to gather context. It looks for `GEMINI.md` files in the current directory, all parent directories up to the project root (`.git`), and all subdirectories. This allows for both global project context and highly specific, localized instructions.

*   **Global Context**: A file in `~/.gemini/` can provide default instructions for all projects.
*   **Project & Ancestor Context**: Files in parent directories provide context for the entire project.
*   **Local Context**: Files in subdirectories provide specific instructions for a particular module or component.

The contents of all found files are combined and sent to the model. Instructions from more specific locations supplement or override those from more general ones.

You can use the following commands to manage this instructional context:

*   `/memory show`: Displays the final combined context being used by the AI.
*   `/memory refresh`: Forces a re-scan and reload of all context files.

## Application Structure and SSOT Code Patterns

## Application Structure

The application follows a microservices architecture, composed of three main components:

1.  **`frontend`**: A React-based single-page application (SPA) responsible for the user interface. It uses Vite for building, Vitest for testing, and Tailwind CSS for styling.

2.  **`backend`**: A FastAPI-based Python service that serves as the main application backend. It handles business logic, data persistence (using PostgreSQL with SQLAlchemy and Alembic for migrations), and communication with other services. It also includes functionality for code analysis (using `tree-sitter`) and interacts with a vector store (Qdrant).

3.  **`render-svc`**: A smaller FastAPI-based Python service dedicated to rendering Markdown content into HTML. This service likely offloads the rendering process from the main backend, allowing for independent scaling and development.

The use of Docker (`docker-compose.yml`, `Dockerfile`) suggests that the application is designed to be containerized and deployed using a container orchestration system (like the `k8s` configuration suggests).

## SSOT Code Patterns

Given the microservices architecture, identifying Single Source of Truth (SSOT) patterns is crucial for maintaining data consistency and avoiding redundancy. Here are some key areas where SSOT principles are likely applied:

### 1. Database as SSOT

The PostgreSQL database, managed by the `backend` service, serves as the primary SSOT for all persistent application data. The use of SQLAlchemy as the ORM and Alembic for database migrations ensures a structured and version-controlled approach to schema management.

**Key Models and Relationships:**

The core of the application's data model revolves around `User`, `Project`, `ChatSession`, and `ChatMessage`.

*   **`User`**: Represents a user account with authentication details. It has a one-to-many relationship with `Project`, `Session`, and `PromptTemplate`.
*   **`Project`**: Acts as a container for `ChatSession`, `CodeDocument`, `KnowledgeDocument`, and `TimelineEvent`, establishing a clear ownership hierarchy.
*   **`ChatSession`**: Represents a single chat conversation and has a one-to-many relationship with `ChatMessage`.
*   **`ChatMessage`**: Stores individual chat messages, including content, role, and associated metadata.
*   **`CodeDocument` and `CodeEmbedding`**: These models are used to store information about the codebase, including parsed symbols, AST metadata, and vector embeddings for semantic search.
*   **`KnowledgeDocument`**: Stores full-text knowledge base entries.
*   **`RuntimeConfig`, `ConfigHistory`, `ModelConfiguration`, `ModelUsageMetrics`**: These models manage the application's dynamic configuration, including LLM settings, and track their usage and history.
*   **`ImportJob`**: Tracks the status of long-running repository import tasks.
*   **`SearchHistory`**: Stores user search queries.
*   **`TimelineEvent`**: Records significant events in a project's lifecycle.

**Schema Evolution and Migrations:**

The `backend/alembic/versions` directory contains a series of migration scripts that document the evolution of the database schema. These migrations handle:

*   **Initial table creation**: The initial schema is defined in the models and created by Alembic.
*   **Adding new features**: New tables like `search_history`, `import_jobs`, and `prompt_templates` are introduced through dedicated migration scripts.
*   **Performance optimizations**: The `005_postgresql_optimizations.py` and `007_comprehensive_postgresql_enhancements.py` migrations introduce various PostgreSQL-specific optimizations, such as:
    *   Using `JSONB` for JSON columns.
    *   Adding GIN and GiST indexes for faster full-text search and trigram matching.
    *   Creating partial indexes for frequently queried subsets of data.
    *   Adding check constraints to enforce data integrity.
*   **Vector storage**: The `migrate_to_pgvector_only.py` and `007_comprehensive_postgresql_enhancements.py` migrations introduce support for `pgvector`, enabling efficient similarity search on vector embeddings.

**Concrete References for Future Development:**

*   **Adding a new model**: Create a new Python file in `backend/app/models`, define the SQLAlchemy model, and then generate a new Alembic migration to create the corresponding table in the database.
*   **Modifying an existing model**: After modifying a model in `backend/app/models`, generate a new Alembic migration to apply the changes to the database schema.
*   **Troubleshooting database issues**: The Alembic migration history provides a clear audit trail of all schema changes, which can be invaluable for debugging database-related problems. The extensive use of indexes and constraints in the migrations also helps to prevent data corruption and performance issues.

### 2. Configuration Management as SSOT

The `backend/app/config.py` file establishes a centralized and validated source of truth for all backend configurations. This is achieved through the use of Pydantic's `BaseSettings`.

**How it Works:**

*   **`Settings` Class**: This Pydantic class defines all application settings as typed attributes.
*   **Environment Variable Loading**: Pydantic automatically loads values from environment variables and `.env` files, overriding the defaults defined in the class.
*   **Validation**: Pydantic performs automatic validation of the loaded values against the type hints. Custom validators, like `validate_vector_store_type`, enforce additional constraints.
*   **Centralized Access**: The `get_settings()` function provides a cached, singleton-like instance of the `Settings` class, ensuring consistent access to configuration values throughout the application.
*   **Startup Checks**: The application performs security checks at startup to ensure that default secrets are not being used in production.

**Concrete References for Future Development:**

*   **Adding a new configuration option**: Add a new attribute to the `Settings` class in `backend/app/config.py`. Provide a type hint and a default value.
*   **Accessing configuration values**: Import the `settings` object from `backend.app.config` and access the configuration values as attributes (e.g., `settings.database_url`).
*   **Environment-specific configuration**: Use a `.env` file to override the default configuration values for different environments (e.g., development, testing, production).

### 3. API Definitions as SSOT

The `backend/app/schemas` directory contains Pydantic models that define the data contracts for the API. These schemas serve as the SSOT for the data structures exchanged between the frontend and backend.

**How it Works:**

*   **Pydantic Schemas**: Each file in the `backend/app/schemas` directory corresponds to a specific domain of the application (e.g., `chat.py`, `project.py`, `user.py`). These files contain Pydantic models that define the shape and validation rules for API requests and responses.
*   **Request and Response Models**: The schemas are used in the FastAPI route handlers to validate incoming request bodies and to serialize outgoing response data. This ensures that all data exchanged between the frontend and backend conforms to the defined contracts.
*   **Automatic API Documentation**: FastAPI uses these Pydantic models to automatically generate interactive API documentation (e.g., Swagger UI, ReDoc). This documentation serves as a live, always-up-to-date reference for the API.

**Concrete References for Future Development:**

*   **Adding a new API endpoint**: Define the request and response models for the new endpoint in the appropriate schema file in `backend/app/schemas`. Then, use these models in the FastAPI route handler to validate the request and serialize the response.
*   **Modifying an existing API endpoint**: Update the corresponding Pydantic models in `backend/app/schemas` to reflect the changes in the API's data contract.
*   **Understanding the API**: The `backend/app/schemas` directory and the auto-generated API documentation are the best places to understand the API's capabilities and data structures.

### 4. Frontend State Management as SSOT

The frontend uses Zustand, a small, fast, and scalable state-management solution, to create a centralized store for the application's UI state. This ensures that different components access and modify the state in a consistent and predictable manner, avoiding state duplication and making the UI more robust.

**How it Works:**

*   **Zustand Stores**: The application defines separate stores for different domains of the application, such as `authStore.js` and `projectStore.js`.
*   **`create` function**: The `create` function from Zustand is used to create a store. It takes a function that defines the store's state and actions.
*   **`persist` middleware**: The `authStore` uses the `persist` middleware to save the store's state to `localStorage`, allowing user preferences and session information to persist across page reloads.
*   **Optimistic Updates**: The `projectStore` implements optimistic updates for a more responsive UI. It immediately updates the UI based on the user's actions and then rolls back the changes if the API request fails.
*   **Async Actions**: The stores define async actions that handle API requests and update the store's state accordingly.

**Concrete References for Future Development:**

*   **Adding a new piece of state**: Add a new attribute to the state object in the relevant Zustand store.
*   **Adding a new action**: Add a new function to the store that uses the `set` function to update the state.
*   **Using the store in a component**: Use the `useAuthStore` or `useProjectStore` hooks in your React components to access the store's state and actions.
*   **Creating a new store**: For a new domain of the application, create a new file in `frontend/src/stores` and use the `create` function from Zustand to define the new store.

### 5. Code Analysis as SSOT

The `backend/app/code_processing/parser.py` file provides a centralized `CodeParser` class that serves as the SSOT for code analysis.

**How it Works:**

*   **`tree-sitter` Integration**: The `CodeParser` class uses the `tree-sitter` library to parse code files and generate abstract syntax trees (ASTs).
*   **Language Support**: The parser supports multiple programming languages, including Python, JavaScript, and TypeScript.
*   **Symbol and Import Extraction**: The parser provides methods for extracting symbols (e.g., functions, classes) and import statements from the AST.
*   **Resilient Design**: The `CodeParser` is designed to be resilient, with a fallback to a no-op stub if `tree-sitter` is not available. This ensures that the application can still run even if the `tree-sitter` library is not installed.

**Concrete References for Future Development:**

*   **Adding support for a new language**: To add support for a new language, you'll need to:
    1.  Add the `tree-sitter` grammar for the new language to the `backend/build/tree-sitter` directory.
    2.  Update the `_load_languages` method in `backend/app/code_processing/parser.py` to load the new language grammar.
    3.  Add the new language to the `symbol_types` and `import_types` dictionaries in the `_extract_symbols` and `_extract_imports` methods, respectively.
*   **Extending the parser's functionality**: You can add new methods to the `CodeParser` class to extract other types of information from the AST, such as comments, annotations, or code complexity metrics.

### 6. Vector Store as SSOT

The application has a flexible and extensible vector store implementation that serves as the SSOT for all vector embeddings. The choice of vector store is determined by the `vector_store_type` setting in `backend/app/config.py`, which can be either `pgvector` or `qdrant`.

**How it Works:**

*   **`VectorServiceProtocol`**: The `backend/app/services/vector_service.py` file defines a `VectorServiceProtocol` that all vector store implementations must adhere to. This ensures a consistent interface for interacting with the vector store, regardless of the underlying technology.
*   **`PostgresVectorService`**: This service, located in `backend/app/services/postgres_vector_service.py`, provides the implementation for the `pgvector` backend. It handles the details of connecting to the PostgreSQL database, creating and querying the vector table, and converting vectors to the format expected by `pgvector`.
*   **`QdrantService`**: This service, located in `backend/app/services/qdrant_service.py`, provides the implementation for the `qdrant` backend. It handles the details of connecting to the Qdrant server, creating and managing collections, and performing vector search and upsert operations.
*   **Configuration-based selection**: The `vector_service` factory function in `backend/app/dependencies.py` uses the `vector_store_type` setting to determine which vector store implementation to instantiate.

**Concrete References for Future Development:**

*   **Adding a new vector store backend**: To add support for a new vector store, you'll need to:
    1.  Create a new service class that implements the `VectorServiceProtocol`.
    2.  Add the new service to the `vector_service` factory function in `backend/app/dependencies.py`.
    3.  Add the necessary configuration options to the `Settings` class in `backend/app/config.py`.
*   **Changing the vector store backend**: To switch between the `pgvector` and `qdrant` backends, simply change the value of the `VECTOR_STORE_TYPE` environment variable.
*   **Extending the vector store's functionality**: You can add new methods to the `VectorServiceProtocol` and then implement them in the `PostgresVectorService` and `QdrantService` classes to add new vector store capabilities.

## Operational Guide

### Common Commands

This section provides a list of common commands for developing and running the application.

#### General

*   `make install`: Install all backend and frontend dependencies.
*   `make dev`: Start the development environment using Docker Compose.
*   `make up`: Start all containers in the background.
*   `make down`: Stop all containers.
*   `make logs`: View the logs of all running containers.
*   `make clean`: Clean up all generated files and containers.

#### Testing

*   `make test`: Run all backend and frontend tests.
*   `cd backend && python3 -m pytest`: Run only the backend tests.
*   `cd frontend && npm test`: Run only the frontend tests.

#### Linting and Formatting

*   `make lint`: Run linters for both the backend and frontend.
*   `make format`: Format the code for both the backend and frontend.

#### Database

*   `make db-reset`: Reset the database.
*   `make db-shell`: Open a shell to the SQLite database.

#### Docker

*   `make build`: Build the Docker images.
*   `make shell-backend`: Open a shell in the backend container.
*   `make shell-frontend`: Open a shell in the frontend container.

### Vite Configuration (`vite.config.js`)

The `frontend/vite.config.js` file configures the Vite development server and build process.

*   **Proxy**: The `server.proxy` option is used to proxy API requests from the frontend to the backend, avoiding CORS issues during development.
*   **HMR (Hot Module Replacement)**: The `server.hmr` option is enabled for a fast development workflow.
*   **Code Splitting**: The `build.rollupOptions.output.manualChunks` option is used to configure code splitting, which can help to improve the application's loading performance.
*   **Polyfills**: The `rollup-plugin-inject` plugin is used to polyfill the `Buffer` object for the browser environment.

### Docker Compose (`docker-compose.yml`)

The `docker-compose.yml` file defines the services, networks, and volumes for the development environment.

*   **Services**: The file defines the following services:
    *   `backend`: The FastAPI backend service.
    *   `redis`: A Redis instance for caching and rate limiting.
    *   `qdrant`: A Qdrant instance for vector search.
    *   `render-svc`: The Markdown rendering service.
    *   `frontend`: The React frontend service.
*   **Volumes**: The file uses volumes to mount the local source code into the containers, allowing for live reloading during development.
*   **Networks**: The services are connected to a custom bridge network called `app-network`, which allows them to communicate with each other using their service names as hostnames.
*   **Healthchecks**: The `healthcheck` option is used to define health checks for the `backend`, `render-svc`, and `frontend` services. This ensures that the services are running correctly before they are marked as healthy.

### Container Management

*   **Starting the environment**: Use `make dev` or `make up` to start the development environment.
*   **Stopping the environment**: Use `make down` to stop the containers.
*   **Restarting containers**: To restart the containers, you can use the following commands:
    *   `make down && make up`: This will stop and then restart all the containers.
    *   `docker-compose restart <service_name>`: This will restart a specific service (e.g., `docker-compose restart backend`).
*   **Viewing logs**: Use `make logs` to view the logs of all running containers, or `docker-compose logs -f <service_name>` to view the logs of a specific service.

### Connecting to the Neon PostgreSQL Database

The application is configured to use a Neon PostgreSQL database in production. The connection string is defined in the `DATABASE_URL` environment variable in the `.env` file.

To connect to the database, you can use a PostgreSQL client like `psql` or a GUI tool like DBeaver or DataGrip. You will need to provide the following connection details, which can be found in the `DATABASE_URL`:

*   **Host**: The hostname of the database server.
*   **Port**: The port number of the database server.
*   **Database**: The name of the database.
*   **User**: The username for connecting to the database.
*   **Password**: The password for the user.

**Example `psql` command:**

```bash
psql "postgresql://<user>:<password>@<host>:<port>/<database>?sslmode=require"
```

### Environment Variables

The application uses `.env` files to manage environment variables. There are several `.env` files in the root directory:

*   `.env.example`: An example file that shows the required environment variables.
*   `.env.production`: Environment variables for the production environment.
*   `.env.ready`: Environment variables for the "ready" environment (likely a staging or pre-production environment).
*   `.env.vector`: Environment variables for the vector store.

The `docker-compose.yml` file uses the `env_file` option to load the `.env` file. To use a different `.env` file, you can either rename it to `.env` or use the `--env-file` command-line option with `docker compose`.

**Example:**

```bash
docker compose --env-file .env.production up
```

### Potential Pitfalls
*   **Multiple `.env` files**: Be aware that there are multiple `.env` files. Make sure you are using the correct one for your environment.
*   **`docker compose` vs `docker-compose`**: This project uses `docker compose` (without a hyphen). Be sure to use the correct command.
*   **`python` vs `python3`**: The `Makefile` uses both `python` and `python3`. To avoid issues, it's best to use `python3` consistently when running Python commands manually.
*   **Virtual Environments**: The backend has a `venv` directory, and the `pyproject.toml` file is configured for `pytest`. When running backend tests or other Python scripts manually, make sure you have activated the virtual environment (`source backend/venv/bin/activate`).
