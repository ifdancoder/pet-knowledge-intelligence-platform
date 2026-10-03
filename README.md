# Knowledge Intelligence Platform

A backend service for ingesting personal knowledge sources (documents, web pages, repositories) and querying them through search and automated analysis. So far it delivers the foundation (FastAPI skeleton with email/password authentication and a multi-tenant Workspace/RBAC model) and the asynchronous ingestion pipeline: upload a PDF or Markdown file, and a chain of Celery tasks extracts its text, normalizes and chunks it, generates embeddings, and indexes it into both Elasticsearch and pgvector. Later sub-projects add hybrid search and RAG conversations on top of this.

## Tech stack

Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async, asyncpg), Alembic, PostgreSQL (via the `pgvector/pgvector` image), argon2-cffi for password hashing, PyJWT for access tokens, `uv` for dependency management. Ingestion pipeline: Celery + RabbitMQ (async task processing), Redis (distributed locking), boto3 + MinIO/S3 (object storage), Elasticsearch (BM25 index), pgvector (semantic index), pypdf (PDF extraction), sentence-transformers / OpenAI (embeddings). Tests run with pytest, pytest-asyncio, and Testcontainers against real Postgres, Elasticsearch, MinIO, and Redis instances.

## Key engineering decisions

- **Hexagonal/Clean Architecture.** Domain entities are plain dataclasses, decoupled from SQLAlchemy; `Workspace` is an aggregate root enforcing its own invariants (e.g. the last-owner rule). Repository adapters map ORM rows to domain entities explicitly at the infrastructure boundary.
- **Refresh token rotation with reuse detection.** Each refresh issues a new refresh token and revokes the old one; presenting an already-revoked token is treated as a compromise signal and revokes the entire token chain for that user.
- **RBAC via a composable FastAPI dependency.** `require_permission(permission)` resolves the caller's workspace membership and checks it against a static `role -> permissions` table, rather than a bespoke authorization layer.
- **EmailSender as a Strategy.** Email verification goes through an `EmailSender` Protocol; the only implementation today is `ConsoleEmailSender` (logs instead of sending), so a real SMTP/SES sender can be added later without touching the service layer.
- **ULIDs for all entity IDs**, assigned by domain factory methods at creation time (not generated as a database default), sortable by creation time.
- **Cascade deletes for workspace membership.** Deleting a workspace cascades to its `workspace_members` rows at the database level, rather than requiring the application to clean them up first.
- **Sync workers, async API.** Celery tasks run synchronously end to end (their own sync SQLAlchemy engine) — the one exception is `SourceLoader.load()`, bridged with a single `asyncio.run()` call inside `ExtractDocumentService`, not spread through the worker. The API stays fully async, with its own async `SourceRepository` adapter for the two operations it needs.
- **Idempotent, lockable pipeline stages.** Each stage checks `Source.status` before acting (safe against retries and duplicate delivery), runs inside a Redis lock keyed by `source_id`, and routes to a RabbitMQ dead-letter queue once retries are exhausted.
- **SourceLoader and EmbeddingProvider as Strategies.** `PdfSourceLoader`/`MarkdownSourceLoader` and `LocalEmbeddingProvider`/`OpenAIEmbeddingProvider` are both Protocol-based variation points, selected by a registry or an environment flag rather than branching inside the pipeline.

## Project structure

Hexagonal/Clean Architecture, organized by layer with feature sub-packages nested inside each:

- `src/domain/` — plain-Python entities and aggregates (`User`, `Workspace`, `Source`, `Chunk`), domain exceptions, and ports (`Protocol` interfaces). No framework or ORM imports.
- `src/application/` — use-case services (`AuthService`, `WorkspaceService`, the five ingestion pipeline-stage services) orchestrating domain entities through ports.
- `src/infrastructure/` — adapters: SQLAlchemy ORM models and repositories, password/JWT utilities, the console email sender, source loaders, embedding providers, S3/MinIO storage, the Elasticsearch indexer, the Redis lock.
- `src/presentation/api/` — FastAPI routers, Pydantic request/response schemas, dependency wiring, and the domain-error-to-HTTP mapping.
- `src/presentation/tasks/` — Celery task functions, the pipeline's other driving adapter (alongside `presentation/api/`).
- `src/worker.py` — Celery app factory (the worker's composition root, parallel to `main.py` for the API).
- `src/shared/` — small cross-cutting utilities used by multiple layers (ULID generation).
- `alembic/` — database migrations.
- `tests/` — pytest suite, mirrors the `src/` layer structure (`tests/domain/`, `tests/application/`, `tests/infrastructure/`, `tests/presentation/`).

## How to run

```bash
uv sync --all-groups
cp .env.example .env
docker compose up -d
export $(cat .env | xargs)
uv run alembic upgrade head
uv run uvicorn main:app --reload --app-dir src
```

The API is now at `http://localhost:8000`.

Start the Celery worker (separate process from the API):

```bash
PYTHONPATH=src uv run celery -A worker worker --loglevel=info
```

## Environment variables

- `DATABASE_URL` — Postgres connection string, e.g. `postgresql+asyncpg://kip:kip@localhost:5434/kip`
- `JWT_SECRET` — secret used to sign access tokens; generate a random value for any non-local environment
- `RABBITMQ_URL`, `REDIS_URL` — broker and locking
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET` — object storage (MinIO locally, real S3 in prod)
- `ELASTICSEARCH_URL` — search index
- `EMBEDDING_PROVIDER` (`local` | `openai`) and `OPENAI_API_KEY` (only required if `openai`)

## API documentation

Interactive docs are auto-generated by FastAPI at `http://localhost:8000/docs` once the server is running.

Example request:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "longenoughpassword"}'
```

## Database migrations

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

## Tests

```bash
uv run pytest -v
```

Unit tests (service layer, against in-memory fake repositories) and integration tests (repositories and full API flows, against real Postgres, Elasticsearch, MinIO, and Redis containers via Testcontainers) live side by side under `tests/`, mirroring the `src/` layer structure. The ingestion pipeline additionally has an orchestration test against fakes (`tests/presentation/tasks/test_ingestion.py`) and a full end-to-end test against real infrastructure (`tests/presentation/tasks/test_ingestion_integration.py`).

## Limitations

- No real email delivery yet — verification tokens are logged, not emailed.
- No password reset flow.
- No rate limiting on auth endpoints yet (planned for the observability/hardening sub-project).
- Only PDF and Markdown source types; Web and Git are future Strategy additions.
- One embedding provider is "active" per deployment; switching requires re-embedding the corpus.
- No search/ranking endpoint yet — the next sub-project queries the Elasticsearch/pgvector data this pipeline writes.

## License

MIT, per `pyproject.toml`.
