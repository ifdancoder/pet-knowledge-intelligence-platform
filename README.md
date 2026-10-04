# Knowledge Intelligence Platform

A backend service for ingesting personal knowledge sources (documents, web pages, repositories) and querying them through search and automated analysis. So far it delivers the foundation (FastAPI skeleton with email/password authentication and a multi-tenant Workspace/RBAC model), the asynchronous ingestion pipeline (upload a PDF or Markdown file, and a chain of Celery tasks extracts its text, normalizes and chunks it, generates embeddings, and indexes it into both Elasticsearch and pgvector), hybrid search (query both indexes, fuse the two rankings, and rerank with a cross-encoder), and RAG conversations: ask a question in a conversation, and the reply is grounded in search results from your own workspace and streamed back token by token over Server-Sent Events.

## Tech stack

Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async, asyncpg), Alembic, PostgreSQL (via the `pgvector/pgvector` image), argon2-cffi for password hashing, PyJWT for access tokens, `uv` for dependency management. Ingestion pipeline: Celery + RabbitMQ (async task processing), Redis (distributed locking), boto3 + MinIO/S3 (object storage), Elasticsearch (BM25 index), pgvector (semantic index), pypdf (PDF extraction), sentence-transformers / OpenAI (embeddings). Search: Reciprocal Rank Fusion over Elasticsearch BM25 and pgvector cosine-similarity results, reranked by a cross-encoder (sentence-transformers). Conversations/RAG: Ollama (local, default) or Anthropic Claude for generation, streamed over Server-Sent Events, grounded in Search's retrieval. Tests run with pytest, pytest-asyncio, and Testcontainers against real Postgres, Elasticsearch, MinIO, and Redis instances.

## Key engineering decisions

- **Hexagonal/Clean Architecture.** Domain entities are plain dataclasses, decoupled from SQLAlchemy; `Workspace` is an aggregate root enforcing its own invariants (e.g. the last-owner rule). Repository adapters map ORM rows to domain entities explicitly at the infrastructure boundary.
- **Refresh token rotation with reuse detection.** Each refresh issues a new refresh token and revokes the old one; presenting an already-revoked token is treated as a compromise signal and revokes the entire token chain for that user.
- **RBAC via a composable FastAPI dependency.** `require_permission(permission)` resolves the caller's workspace membership and checks it against a static `role -> permissions` table, rather than a bespoke authorization layer.
- **EmailSender as a Strategy.** Email verification goes through an `EmailSender` Protocol; the only implementation today is `ConsoleEmailSender` (logs instead of sending), so a real SMTP/SES sender can be added later without touching the service layer.
- **ULIDs for all entity IDs**, assigned by domain factory methods at creation time (not generated as a database default), sortable by creation time.
- **Cascade deletes for workspace membership.** Deleting a workspace cascades to its `workspace_members` rows at the database level, rather than requiring the application to clean them up first.
- **Sync workers, async API.** Celery tasks run synchronously end to end (their own sync SQLAlchemy engine) — the one exception is `SourceLoader.load()`, bridged with a single `asyncio.run()` call inside `ExtractDocumentCommandHandler`, not spread through the worker. The API stays fully async, with its own async `SourceRepository` adapter for the two operations it needs.
- **Idempotent, lockable pipeline stages.** Each stage checks `Source.status` before acting (safe against retries and duplicate delivery), runs inside a Redis lock keyed by `source_id`, and routes to a RabbitMQ dead-letter queue once retries are exhausted.
- **SourceLoader and EmbeddingProvider as Strategies.** `PdfSourceLoader`/`MarkdownSourceLoader` and `LocalEmbeddingProvider`/`OpenAIEmbeddingProvider` are both Protocol-based variation points, selected by a registry or an environment flag rather than branching inside the pipeline.
- **CQRS at the application layer.** Every use case is an explicit `Command`/`Query` dataclass plus a single-method handler, not a multi-method service class. Commands return `None`, except for two narrow, explicit exceptions: creation commands return only the new entity's id (needed to build the response or a follow-up query), and `LoginCommand`/`RefreshCommand` return their issued tokens (an ephemeral secret — only the hash is ever persisted, so there is no query that could recover it afterward). No Command/Query Bus: handlers are constructed and invoked the same way the services they replaced were, via `Depends()`.
- **Decorator for reranking.** `RerankingSearchQueryHandler` wraps `HybridSearchQueryHandler` — both implement the same `handle(query) -> list[SearchResult]` shape. The inner handler fetches a fixed candidate pool (at least 20, or `limit` if larger) and never applies the caller's `limit` itself; only the outer decorator does, after the cross-encoder has had the full pool to rerank.
- **Rank-based fusion, not score-based.** BM25 scores and cosine similarities live on incomparable scales, so Reciprocal Rank Fusion combines the two rankings using only each hit's rank position, never its raw score — no normalization step, no magic weighting coefficient to tune.
- **A streaming use case gets its own honest name, not a fake Handler.** `GenerateAssistantReplyService` is deliberately not called a Command/QueryHandler — its `stream(...) -> AsyncIterator[str]` shape is genuinely different from every other handler's `handle(x) -> None/id/entity`, and naming it like the rest would misrepresent what it does.
- **Provenance, not claimed citations.** An assistant message's `source_chunk_ids` is every chunk that was in its context window — not an attempt to parse which ones the model actually drew on, which would need fragile output parsing for no real gain in honesty.
- **One cross-feature application dependency, justified explicitly.** `GenerateAssistantReplyService` depends on Search's concrete `RerankingSearchQueryHandler` rather than a new Protocol — introducing a Protocol to decouple from the one and only Search implementation would be abstraction with nothing to abstract away.

## Project structure

Hexagonal/Clean Architecture, organized by layer with feature sub-packages nested inside each:

- `src/domain/` — plain-Python entities and aggregates (`User`, `Workspace`, `Source`, `Chunk`), domain exceptions, and ports (`Protocol` interfaces). No framework or ORM imports.
- `src/application/` — use cases as `Command`/`Query` dataclasses plus single-method `Handler` classes, orchestrating domain entities through ports.
- `src/infrastructure/` — adapters: SQLAlchemy ORM models and repositories, password/JWT utilities, the console email sender, source loaders, embedding providers, S3/MinIO storage, the Elasticsearch indexer, the Redis lock.
- `src/presentation/api/` — FastAPI routers, Pydantic request/response schemas, dependency wiring, and the domain-error-to-HTTP mapping.
- `src/presentation/tasks/` — Celery task functions, the pipeline's other driving adapter (alongside `presentation/api/`).
- `src/domain/search/`, `src/application/search/`, `src/infrastructure/search/`, `src/presentation/api/search/` — the Search feature's four layers, parallel to Ingestion's.
- `src/domain/conversations/`, `src/application/conversations/`, `src/infrastructure/conversations/`, `src/presentation/api/conversations/` — the Conversations/RAG feature's four layers.
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
- `EMBEDDING_DEVICE` (`cpu` | `cuda`, default `cpu`, only used by the `local` provider) — `cuda` is only safe if the worker's Celery pool is also switched away from the default prefork pool (e.g. `celery worker --pool=solo`), since torch forbids re-initializing CUDA inside a forked process
- `LLM_PROVIDER` (`local` | `anthropic`, default `local`) — which LLM backend generates conversation replies
- `OLLAMA_URL`, `OLLAMA_MODEL` (default `llama3.2:1b`) — only used by the `local` provider; run `docker compose exec ollama ollama pull llama3.2:1b` once after first starting the stack
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (default `claude-sonnet-5`) — only required if `anthropic`

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

Unit tests (service layer, against in-memory fake repositories) and integration tests (repositories and full API flows, against real Postgres, Elasticsearch, MinIO, and Redis containers via Testcontainers) live side by side under `tests/`, mirroring the `src/` layer structure. The ingestion pipeline additionally has an orchestration test against fakes (`tests/presentation/tasks/test_ingestion.py`) and a full end-to-end test against real infrastructure (`tests/presentation/tasks/test_ingestion_integration.py`); Search has the equivalent end-to-end test against the real pipeline output (`tests/presentation/api/search/test_search_integration.py`); Conversations/RAG has the equivalent against real Postgres and Elasticsearch, with the LLM always faked (`tests/presentation/api/conversations/test_rag_integration.py`).

## Limitations

- No real email delivery yet — verification tokens are logged, not emailed.
- No password reset flow.
- No rate limiting on auth endpoints yet (planned for the observability/hardening sub-project).
- Only PDF and Markdown source types; Web and Git are future Strategy additions.
- One embedding provider is "active" per deployment; switching requires re-embedding the corpus.
- Search has no pagination — a single ranked list, capped at 50 results.
- No snippet highlighting — each result returns the full (short) chunk text.
- Conversations have no titles and cannot be renamed.
- No context-window management — the full message history is sent to the LLM every turn; very long conversations will eventually hit the model's context limit.
- No retry or fallback between LLM providers — one is active per deployment (`LLM_PROVIDER`).

## License

MIT, per `pyproject.toml`.
