# Knowledge Intelligence Platform

A backend service for ingesting personal knowledge sources (documents, web pages, repositories) and querying them through search and automated analysis. So far it delivers the foundation (FastAPI skeleton with email/password authentication and a multi-tenant Workspace/RBAC model), the asynchronous ingestion pipeline (upload a PDF or Markdown file, and a chain of Celery tasks extracts its text, normalizes and chunks it, generates embeddings, and indexes it into both Elasticsearch and pgvector), hybrid search (query both indexes, fuse the two rankings, and rerank with a cross-encoder), and RAG conversations: ask a question in a conversation, and the reply is grounded in search results from your own workspace and streamed back token by token over Server-Sent Events.

## Tech stack

Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async, asyncpg), Alembic, PostgreSQL (via the `pgvector/pgvector` image), argon2-cffi for password hashing, PyJWT for access tokens, `uv` for dependency management. Ingestion pipeline: Celery + RabbitMQ (async task processing), Redis (distributed locking), boto3 + MinIO/S3 (object storage), Elasticsearch (BM25 index), pgvector (semantic index), pypdf (PDF extraction), sentence-transformers / OpenAI (embeddings). Search: Reciprocal Rank Fusion over Elasticsearch BM25 and pgvector cosine-similarity results, reranked by a cross-encoder (sentence-transformers). Conversations/RAG: Ollama (local, default) or Anthropic Claude for generation, streamed over Server-Sent Events, grounded in Search's retrieval. Observability: structured JSON logging correlated with OpenTelemetry traces (OTLP over gRPC to Grafana Tempo), Prometheus metrics (auto-instrumented HTTP metrics plus custom ingestion/RAG duration histograms) visualized in a provisioned Grafana dashboard, Sentry for unexpected-error capture. Rate limiting on auth endpoints via a Redis-backed fixed-window counter. Tests run with pytest, pytest-asyncio, and Testcontainers against real Postgres, Elasticsearch, MinIO, and Redis instances.

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
- **Tracing spans both processes, not just the API.** `opentelemetry-instrumentation-celery` propagates trace context through Celery's task message headers, so a single source-upload request's trace connects the HTTP call to the asynchronous pipeline it triggers — this is the one case in the system where a single logical operation genuinely crosses a process boundary.
- **Custom metrics stay out of the application layer.** `rag_generation_duration_seconds` is recorded in the router (the composition-root layer that already wires concrete infrastructure classes directly), not inside `GenerateAssistantReplyService` — importing `prometheus_client` into the application layer would be an infrastructure leak for no real benefit.
- **Expected business errors never reach Sentry.** The `DomainError` exception handler and the catch-all `Exception` handler are intentionally asymmetric: only the latter calls `sentry_sdk.capture_exception` — a wrong password or a 404 is not a bug, and reporting every 4xx would drown out the errors that actually matter.
- **Rate limiting keyed by IP, not by email.** `/auth/login`, `/register`, and `/refresh` share one dependency factory keyed by `request.client.host` — the one identifier available consistently across all three without parsing each request body differently, and IP-based brute-forcing is the actual threat model here.

## Project structure

Hexagonal/Clean Architecture, organized by layer with feature sub-packages nested inside each:

- `src/domain/` — plain-Python entities and aggregates (`User`, `Workspace`, `Source`, `Chunk`), domain exceptions, and ports (`Protocol` interfaces). No framework or ORM imports.
- `src/application/` — use cases as `Command`/`Query` dataclasses plus single-method `Handler` classes, orchestrating domain entities through ports.
- `src/infrastructure/` — adapters: SQLAlchemy ORM models and repositories, password/JWT utilities, the console email sender, source loaders, embedding providers, S3/MinIO storage, the Elasticsearch indexer, the Redis lock.
- `src/presentation/api/` — FastAPI routers, Pydantic request/response schemas, dependency wiring, and the domain-error-to-HTTP mapping.
- `src/presentation/tasks/` — Celery task functions, the pipeline's other driving adapter (alongside `presentation/api/`).
- `src/domain/search/`, `src/application/search/`, `src/infrastructure/search/`, `src/presentation/api/search/` — the Search feature's four layers, parallel to Ingestion's.
- `src/domain/conversations/`, `src/application/conversations/`, `src/infrastructure/conversations/`, `src/presentation/api/conversations/` — the Conversations/RAG feature's four layers.
- `src/infrastructure/observability/` — structured logging, OpenTelemetry tracing setup, custom Prometheus metrics, Sentry init, composed by one `configure_observability()` bootstrap called from both `main.py` and `worker.py`.
- `src/infrastructure/ratelimit/` — the `RateLimiter` port and its Redis-backed implementation.
- `observability/` — checked-in Tempo/Prometheus config and Grafana datasource/dashboard provisioning, mounted into their respective containers by `docker-compose.yml`.
- `Dockerfile` — multi-stage build (plain `python:3.13-slim`, GPU support via PyTorch's own CUDA wheel, no CUDA base image needed), shared by the API and worker; same image, different command.
- `k8s/` — plain Kubernetes manifests (no Helm) for the entire stack, one `kip` namespace.
- `src/worker.py` — Celery app factory (the worker's composition root, parallel to `main.py` for the API).
- `src/shared/` — small cross-cutting utilities used by multiple layers (ULID generation).
- `alembic/` — database migrations.
- `tests/` — pytest suite, mirrors the `src/` layer structure (`tests/domain/`, `tests/application/`, `tests/infrastructure/`, `tests/presentation/`).
- `.github/workflows/` — CI (lint + test on every push/PR to `main`).

## How to run

**Full stack, including the API and worker:**

```bash
cp .env.example .env
docker compose up -d --build
```

The API is now at `http://localhost:8001` (shifted from the container's internal `8000` to avoid colliding with other local projects, same reasoning as Postgres's `5434`/Redis's `6380` below). Requires `nvidia-container-toolkit` on the host for GPU-accelerated embeddings/reranking — see "GPU support" below. On a host without a GPU, remove the `deploy.resources.reservations.devices` block from the `api`, `worker`, and `ollama` services in `docker-compose.yml` and set `EMBEDDING_DEVICE`/`RERANKER_DEVICE` to `cpu`.

**Host-based dev workflow** (faster iteration — `--reload`, no image rebuild per change):

```bash
uv sync --all-groups
cp .env.example .env
docker compose up -d postgres rabbitmq redis minio elasticsearch ollama tempo prometheus grafana
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
- `RERANKER_DEVICE` (`cpu` | `cuda`, default `cpu`) — device for the cross-encoder reranker; runs inside the API process, which never forks per-request, so `cuda` carries none of `EMBEDDING_DEVICE`'s fork-safety hazard
- `LLM_PROVIDER` (`local` | `anthropic`, default `local`) — which LLM backend generates conversation replies
- `OLLAMA_URL`, `OLLAMA_MODEL` (default `llama3.2:1b`) — only used by the `local` provider; run `docker compose exec ollama ollama pull llama3.2:1b` once after first starting the stack
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (default `claude-sonnet-5`) — only required if `anthropic`
- `OTEL_EXPORTER_OTLP_ENDPOINT` — where traces are exported (default `http://localhost:4317`, Tempo's OTLP gRPC port); if unreachable, spans are silently dropped rather than breaking a request
- `SENTRY_DSN` — optional; unset or empty means Sentry is a no-op
- `METRICS_PORT` — the Celery worker's own Prometheus metrics server port (default `9001`), separate from the API's `/metrics`

## GPU support

The `Dockerfile` is plain `python:3.13-slim` — no CUDA base image needed, since PyTorch's CUDA wheel (already what `uv.lock` resolves by default) bundles its own CUDA runtime via pip. Verified empirically on this machine: a throwaway image on this base, run with `--gpus all`, correctly reported `torch.cuda.is_available() == True` and named the host's GPU.

GPU passthrough into a plain `docker run`/Kubernetes container still requires `nvidia-container-toolkit` on the host:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Verify it worked: `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` should print your GPU. In Kubernetes, GPU scheduling additionally requires the cluster to have the NVIDIA device plugin installed — without it, the `api`, `worker`, and `ollama` Pods (each requesting `nvidia.com/gpu: 1`) stay `Pending` with an `Insufficient nvidia.com/gpu` event. `EMBEDDING_DEVICE=cuda` requires the worker to run with Celery's `--pool=solo` (not the default prefork pool), since torch forbids re-initializing CUDA inside a forked process — the `worker` Deployment in `k8s/worker.yaml` already overrides the command for this reason.

## Kubernetes

Plain manifests (no Helm) in `k8s/`, covering the entire stack — every infrastructure dependency plus the API and worker — in one `kip` namespace: `StatefulSet`s with `volumeClaimTemplates` for the four components where losing data on restart would hurt (`postgres`, `minio`, `elasticsearch`, `ollama`'s model cache), plain `Deployment`s for everything else, a `ConfigMap` (`kip-config`) for non-secret environment variables pointing at cluster-internal DNS names (`postgres.kip.svc.cluster.local`, etc.), and one `Secret` (`kip-secrets`) checked in with placeholder/local-dev values — fill in real ones before applying anywhere but a local cluster.

```bash
docker build -t kip:latest .
# load the locally-built image into your cluster — exact command depends on the tool:
kind load docker-image kip:latest --name <cluster-name>        # kind
minikube image load kip:latest                                  # minikube

# fill in real values in k8s/secret.yaml before applying anywhere but a local cluster
kubectl apply -f k8s/
kubectl get pods -n kip
```

No image registry is used — the image is built locally and loaded directly into the cluster (`imagePullPolicy: IfNotPresent`), consistent with this being a demo/local deployment rather than a managed one. On a cluster without the NVIDIA device plugin, the `api`, `worker`, and `ollama` Pods stay `Pending` (`Insufficient nvidia.com/gpu`) — expected, not a bug; every other component (`postgres`, `rabbitmq`, `redis`, `minio`, `elasticsearch`, `tempo`, `prometheus`, `grafana`) still reaches `Running`.

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
uv run pytest -v                        # everything
uv run pytest -v -m "not integration"   # fast inner loop, no Docker needed
uv run pytest -v -m integration         # just the Testcontainers-backed tests
```

Unit tests (service layer, against in-memory fake repositories) and integration tests (repositories and full API flows, against real Postgres, Elasticsearch, MinIO, and Redis containers via Testcontainers) live side by side under `tests/`, mirroring the `src/` layer structure. The ingestion pipeline additionally has an orchestration test against fakes (`tests/presentation/tasks/test_ingestion.py`) and a full end-to-end test against real infrastructure (`tests/presentation/tasks/test_ingestion_integration.py`); Search has the equivalent end-to-end test against the real pipeline output (`tests/presentation/api/search/test_search_integration.py`); Conversations/RAG has the equivalent against real Postgres and Elasticsearch, with the LLM always faked (`tests/presentation/api/conversations/test_rag_integration.py`). Observability has its own focused tests: Redis-backed rate limiting against a real Redis (Testcontainers), JSON log formatting and trace-context injection, tracing (via OpenTelemetry's `InMemorySpanExporter`, no real Tempo needed), the custom Prometheus histograms, and Sentry capture behavior (mocked, never a real network call).

Tests that need real infrastructure (Postgres, Elasticsearch, MinIO, Redis, via Testcontainers) are marked `@pytest.mark.integration` (124 fast / 50 integration, of 174 total); everything else needs no Docker at all.

## Continuous Integration

`.github/workflows/ci.yml` runs on every push/PR to `main`: a `lint` job (Ruff, mypy strict) and a `test` job (the full suite, including the Testcontainers-backed tests — GitHub-hosted runners already have Docker). No Docker image is built or pushed in CI; that stays a manual step.

## Limitations

- No real email delivery yet — verification tokens are logged, not emailed.
- No password reset flow.
- Only PDF and Markdown source types; Web and Git are future Strategy additions.
- One embedding provider is "active" per deployment; switching requires re-embedding the corpus.
- Search has no pagination — a single ranked list, capped at 50 results.
- No snippet highlighting — each result returns the full (short) chunk text.
- Conversations have no titles and cannot be renamed.
- No context-window management — the full message history is sent to the LLM every turn; very long conversations will eventually hit the model's context limit.
- No retry or fallback between LLM providers — one is active per deployment (`LLM_PROVIDER`).
- Rate limiting is fixed (not configurable) and applies only to `/auth/login`, `/auth/register`, `/auth/refresh`, keyed by client IP.
- No log aggregation (Loki) — logs are JSON on stdout, viewable via `docker compose logs` or the running process's terminal.
- No alerting rules configured in Prometheus or Grafana.
- Sentry performance monitoring/profiling is disabled — error capture only.
- Kubernetes manifests assume a cluster with the NVIDIA device plugin for GPU scheduling. They validate cleanly against the real Kubernetes 1.29 API schema and have no dangling Secret/ConfigMap references, but have not been applied to a live cluster — minikube and kind both failed to bring up a healthy kubelet in this development sandbox (a nested-container/cgroup limitation of that environment, unrelated to the manifests), so a `kubectl apply -f k8s/` smoke test on a real local or managed cluster is still outstanding.
- No image registry/push automation — building and loading the image into a cluster is a manual step.
- The GitHub Actions workflow is written and YAML-validated but unverified end-to-end — this repo has no remote configured, so it has never actually run; it will the first time this is pushed to GitHub.

## License

MIT, per `pyproject.toml`.
