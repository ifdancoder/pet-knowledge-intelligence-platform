# Knowledge Intelligence Platform

*English version: [README.md](README.md)*

Backend-сервис для загрузки личных источников знаний (документов, веб-страниц, репозиториев) и их поиска через гибридный поиск и автоматический анализ. На текущий момент реализовано: фундамент (скелет на FastAPI с аутентификацией по email/паролю и мультитенантной моделью Workspace/RBAC), асинхронный пайплайн загрузки (загружаешь PDF или Markdown-файл, и цепочка Celery-задач извлекает текст, нормализует и разбивает его на чанки, генерирует эмбеддинги и индексирует их в Elasticsearch и pgvector), гибридный поиск (запрос идёт в оба индекса, ранжирования объединяются, результат переранжируется cross-encoder'ом) и RAG-диалоги: задаёшь вопрос в беседе, и ответ строится на результатах поиска из своего workspace и стримится токен за токеном через Server-Sent Events.

## Технологический стек

Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async, asyncpg), Alembic, PostgreSQL (образ `pgvector/pgvector`), argon2-cffi для хеширования паролей, PyJWT для access-токенов, `uv` для управления зависимостями. Пайплайн загрузки: Celery + RabbitMQ (асинхронная обработка задач), Redis (распределённые блокировки), boto3 + MinIO/S3 (объектное хранилище), Elasticsearch (BM25-индекс), pgvector (семантический индекс), pypdf (извлечение текста из PDF), sentence-transformers / OpenAI (эмбеддинги). Поиск: Reciprocal Rank Fusion над результатами Elasticsearch BM25 и pgvector cosine-similarity, переранжирование cross-encoder'ом (sentence-transformers). Диалоги/RAG: Ollama (локально, по умолчанию) или Anthropic Claude для генерации, стриминг через Server-Sent Events, привязка к выдаче поиска. Observability: структурированное JSON-логирование, связанное с трейсами OpenTelemetry (OTLP по gRPC в Grafana Tempo), метрики Prometheus (авто-инструментированные HTTP-метрики плюс кастомные гистограммы длительности загрузки/RAG), визуализация в прошитом дашборде Grafana, Sentry для перехвата неожиданных ошибок. Rate limiting на auth-эндпоинтах через Redis-based fixed-window счётчик. Тесты через pytest, pytest-asyncio и Testcontainers против настоящих Postgres, Elasticsearch, MinIO и Redis.

## Ключевые инженерные решения

- **Hexagonal/Clean Architecture.** Доменные сущности оформлены как простые dataclass'ы, не зависящие от SQLAlchemy; `Workspace` выступает aggregate root'ом, сам проверяющим свои инварианты (например, правило последнего владельца). Репозитории-адаптеры явно маппят строки ORM на доменные сущности на границе инфраструктурного слоя.
- **Ротация refresh-токенов с детекцией повторного использования.** Каждый refresh выпускает новый refresh-токен и отзывает старый; предъявление уже отозванного токена трактуется как сигнал компрометации и отзывает всю цепочку токенов пользователя.
- **RBAC через композируемую зависимость FastAPI.** `require_permission(permission)` резолвит membership вызывающего в workspace и проверяет его против статической таблицы `role -> permissions`, а не через отдельный слой авторизации.
- **EmailSender как Strategy.** Верификация email идёт через Protocol `EmailSender`; единственная реализация сегодня: `ConsoleEmailSender` (логирует вместо отправки), так что настоящий SMTP/SES-отправитель можно добавить позже без изменений в сервисном слое.
- **ULID для всех идентификаторов сущностей**, назначаемые доменными фабричными методами в момент создания (а не как дефолт базы данных), сортируемые по времени создания.
- **Каскадное удаление членства в workspace.** Удаление workspace каскадно удаляет строки `workspace_members` на уровне базы данных, а не требует, чтобы приложение чистило их самостоятельно.
- **Синхронные воркеры, асинхронный API.** Задачи Celery выполняются полностью синхронно, на собственном синхронном SQLAlchemy engine. Единственное исключение: `SourceLoader.load()`, перекинутое одним вызовом `asyncio.run()` внутри `ExtractDocumentCommandHandler`, а не разбросанное по воркеру. API остаётся полностью асинхронным, со своим асинхронным адаптером `SourceRepository` для двух нужных ему операций.
- **Идемпотентные, блокируемые стадии пайплайна.** Каждая стадия проверяет `Source.status` перед действием (безопасно против повторов и дублирующей доставки), выполняется под Redis-блокировкой по ключу `source_id` и отправляется в dead-letter очередь RabbitMQ после исчерпания попыток.
- **SourceLoader и EmbeddingProvider как Strategies.** `PdfSourceLoader`/`MarkdownSourceLoader` и `LocalEmbeddingProvider`/`OpenAIEmbeddingProvider` выступают точками вариативности на основе Protocol, выбираемыми через реестр или переменную окружения, а не через ветвление внутри пайплайна.
- **CQRS на уровне application layer.** Каждый юзкейс оформлен как явный dataclass `Command`/`Query` плюс однометодный handler, а не многометодный сервисный класс. Команды возвращают `None`, за двумя узкими явными исключениями: команды создания возвращают только id новой сущности (нужен для ответа или последующего запроса), а `LoginCommand`/`RefreshCommand` возвращают выпущенные токены (эфемерный секрет: персистится только хеш, так что никакой запрос не сможет восстановить его позже). Без Command/Query Bus: handler'ы конструируются и вызываются так же, как раньше вызывались заменённые ими сервисы, через `Depends()`.
- **Decorator для переранжирования.** `RerankingSearchQueryHandler` оборачивает `HybridSearchQueryHandler`; оба реализуют одну и ту же форму `handle(query) -> list[SearchResult]`. Внутренний handler забирает фиксированный пул кандидатов (минимум 20, либо `limit`, если он больше) и никогда не применяет `limit` вызывающего сам; это делает только внешний декоратор, после того как cross-encoder получил весь пул для переранжирования.
- **Фьюжн по рангам, а не по скорам.** Скоры BM25 и косинусное сходство живут на несопоставимых шкалах, поэтому Reciprocal Rank Fusion объединяет два ранжирования, используя только позицию ранга каждого хита, никогда не его собственный скор. Никакой нормализации, никакого магического весового коэффициента для подбора.
- **У стримингового юзкейса своё честное имя, а не фальшивый Handler.** `GenerateAssistantReplyService` намеренно не называется Command/QueryHandler: форма `stream(...) -> AsyncIterator[str]` реально отличается от формы `handle(x) -> None/id/entity` у всех остальных handler'ов, и называть его так же было бы искажением того, что он делает.
- **Происхождение, а не заявленные цитаты.** `source_chunk_ids` ответа ассистента содержит каждый чанк, что был в его контекстном окне, а не попытка разобрать, какие из них модель реально использовала, что потребовало бы хрупкого парсинга вывода без реального выигрыша в честности.
- **Одна межфичевая зависимость application-слоя, явно обоснованная.** `GenerateAssistantReplyService` зависит от конкретного `RerankingSearchQueryHandler` поиска, а не от нового Protocol: вводить Protocol, чтобы отделиться от единственной реализации поиска, было бы абстракцией без того, от чего абстрагироваться.
- **Трассировка покрывает оба процесса, а не только API.** `opentelemetry-instrumentation-celery` протягивает контекст трейса через заголовки сообщений Celery, так что трейс одного запроса на загрузку документа связывает HTTP-вызов с асинхронным пайплайном, который он запускает. Это единственный случай в системе, где одна логическая операция реально пересекает границу процесса.
- **Кастомные метрики не лезут в application layer.** `rag_generation_duration_seconds` записывается в роутере (слое композиции, который уже напрямую подключает конкретные инфраструктурные классы), а не внутри `GenerateAssistantReplyService`: импорт `prometheus_client` в application layer был бы утечкой инфраструктуры без реальной пользы.
- **Ожидаемые бизнес-ошибки никогда не долетают до Sentry.** Обработчик `DomainError` и catch-all обработчик `Exception` намеренно асимметричны: только второй вызывает `sentry_sdk.capture_exception`. Неверный пароль или 404 не являются багом, а репортинг каждого 4xx утопил бы те ошибки, что реально важны.
- **Rate limiting по IP, а не по email.** `/auth/login`, `/register` и `/refresh` делят одну фабрику зависимости, ключом служит `request.client.host`, единственный идентификатор, доступный одинаково во всех трёх без разбора тела запроса по-разному каждый раз, и брутфорс по IP здесь реальная модель угрозы.

## Структура проекта

Hexagonal/Clean Architecture, организация по слоям с вложенными фиче-поддиректориями в каждом:

- `src/domain/`: чистые Python-сущности и агрегаты (`User`, `Workspace`, `Source`, `Chunk`), доменные исключения и порты (интерфейсы `Protocol`). Без импортов фреймворка или ORM.
- `src/application/`: юзкейсы как dataclass'ы `Command`/`Query` плюс однометодные классы `Handler`, оркестрирующие доменные сущности через порты.
- `src/infrastructure/`: адаптеры, включая ORM-модели и репозитории SQLAlchemy, утилиты пароля/JWT, консольный отправитель email, загрузчики источников, провайдеры эмбеддингов, хранилище S3/MinIO, индексатор Elasticsearch, Redis-блокировку.
- `src/presentation/api/`: роутеры FastAPI, Pydantic-схемы запросов/ответов, прошивка зависимостей и маппинг доменных ошибок в HTTP.
- `src/presentation/tasks/`: функции-задачи Celery, второй driving-адаптер пайплайна (наряду с `presentation/api/`).
- `src/domain/search/`, `src/application/search/`, `src/infrastructure/search/`, `src/presentation/api/search/`: четыре слоя фичи Search, параллельные слоям Ingestion.
- `src/domain/conversations/`, `src/application/conversations/`, `src/infrastructure/conversations/`, `src/presentation/api/conversations/`: четыре слоя фичи Conversations/RAG.
- `src/infrastructure/observability/`: структурированное логирование, настройка трассировки OpenTelemetry, кастомные метрики Prometheus, инициализация Sentry, всё собрано одним бутстрапом `configure_observability()`, вызываемым и из `main.py`, и из `worker.py`.
- `src/infrastructure/ratelimit/`: порт `RateLimiter` и его Redis-based реализация.
- `observability/`: прошитый конфиг Tempo/Prometheus и provisioning datasource/dashboard для Grafana, монтируемые в соответствующие контейнеры через `docker-compose.yml`.
- `Dockerfile`: multi-stage сборка (обычный `python:3.13-slim`, поддержка GPU через собственный CUDA-wheel PyTorch, без необходимости в CUDA-образе), общий для API и воркера; один образ, разные команды.
- `k8s/`: обычные манифесты Kubernetes (без Helm) для всего стека, один namespace `kip`.
- `src/worker.py`: фабрика Celery-приложения (composition root воркера, параллельный `main.py` для API).
- `src/shared/`: мелкие сквозные утилиты, используемые несколькими слоями (генерация ULID).
- `alembic/`: миграции базы данных.
- `tests/`: набор pytest, повторяет структуру слоёв `src/` (`tests/domain/`, `tests/application/`, `tests/infrastructure/`, `tests/presentation/`).
- `.github/workflows/`: CI (lint + тесты на каждый push/PR в `main`).
- `docs/openapi.json`: экспортированная OpenAPI 3.1 схема, сгенерированная прямо из запущенного FastAPI-приложения, чтобы можно было смотреть поверхность API без запуска сервера.

## Как запустить

**Весь стек, включая API и воркер:**

```bash
cp .env.example .env
docker compose up -d --build
```

API теперь доступен на `http://localhost:8001` (смещён с внутреннего `8000` контейнера, чтобы не конфликтовать с другими локальными проектами, та же причина, что и у `5434` для Postgres/`6380` для Redis ниже). Требует `nvidia-container-toolkit` на хосте для GPU-ускоренных эмбеддингов/переранжирования, см. "Поддержка GPU" ниже. На хосте без GPU убери блок `deploy.resources.reservations.devices` из сервисов `api`, `worker` и `ollama` в `docker-compose.yml` и поставь `EMBEDDING_DEVICE`/`RERANKER_DEVICE` в `cpu`.

**Разработка на хосте** (быстрее итерации, `--reload`, без пересборки образа на каждое изменение):

```bash
uv sync --all-groups
cp .env.example .env
docker compose up -d postgres rabbitmq redis minio elasticsearch ollama tempo prometheus grafana
export $(cat .env | xargs)
uv run alembic upgrade head
uv run uvicorn main:app --reload --app-dir src
```

API теперь доступен на `http://localhost:8000`.

Запуск Celery-воркера (отдельный процесс от API):

```bash
PYTHONPATH=src uv run celery -A worker worker --loglevel=info
```

## Фронтенд

React SPA в `frontend/` покрывает MVP-сценарий: регистрация, подтверждение почты, вход, выбор или создание воркспейса, загрузка источника с отслеживанием статуса обработки, поиск по нему и чат с ним через стриминговый RAG-эндпоинт.

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Фронтенд теперь доступен на `http://localhost:5173`. API должен быть уже запущен (см. выше) с `FRONTEND_ORIGIN=http://localhost:5173`, чтобы CORS пропускал запросы от dev-сервера.

Тесты запускаются командой `cd frontend && npm test`.

## Переменные окружения

- `DATABASE_URL`: строка подключения к Postgres, например `postgresql+asyncpg://kip:kip@localhost:5434/kip`
- `JWT_SECRET`: секрет для подписи access-токенов; сгенерируй случайное значение для любой среды, кроме локальной
- `RABBITMQ_URL`, `REDIS_URL`: брокер и блокировки
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`: объектное хранилище (MinIO локально, реальный S3 в проде)
- `ELASTICSEARCH_URL`: индекс поиска
- `EMBEDDING_PROVIDER` (`local` | `openai`) и `OPENAI_API_KEY` (нужен только при `openai`)
- `EMBEDDING_DEVICE` (`cpu` | `cuda`, по умолчанию `cpu`, используется только провайдером `local`): `cuda` безопасна только если пул Celery у воркера также переключён с дефолтного prefork (например, `celery worker --pool=solo`), так как torch запрещает повторную инициализацию CUDA внутри форкнутого процесса
- `RERANKER_DEVICE` (`cpu` | `cuda`, по умолчанию `cpu`): устройство для cross-encoder переранжирования. Он работает внутри процесса API, который никогда не форкается на запрос, поэтому `cuda` не несёт риска форк-безопасности, в отличие от `EMBEDDING_DEVICE`
- `LLM_PROVIDER` (`local` | `anthropic`, по умолчанию `local`): какой LLM-backend генерирует ответы в диалогах
- `OLLAMA_URL`, `OLLAMA_MODEL` (по умолчанию `llama3.2:1b`): используется только провайдером `local`; запусти `docker compose exec ollama ollama pull llama3.2:1b` один раз после первого старта стека
- `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` (по умолчанию `claude-sonnet-5`): нужен только при `anthropic`
- `OTEL_EXPORTER_OTLP_ENDPOINT`: куда экспортируются трейсы (по умолчанию `http://localhost:4317`, OTLP gRPC порт Tempo). Если недоступен, спаны просто молча отбрасываются, а не ломают запрос
- `SENTRY_DSN`: опционально; пустое значение означает, что Sentry работает как no-op
- `METRICS_PORT`: собственный порт сервера метрик Prometheus у Celery-воркера (по умолчанию `9001`), отдельный от `/metrics` у API
- `FRONTEND_ORIGIN`: origin dev-сервера фронтенда, разрешённый через CORS (по умолчанию `http://localhost:5173`)

## Поддержка GPU

`Dockerfile` использует обычный `python:3.13-slim`: CUDA-образ не нужен, так как CUDA-wheel PyTorch (уже то, что по умолчанию резолвит `uv.lock`) несёт в себе собственный CUDA-рантайм через pip. Проверено эмпирически на этой машине: черновой образ на этой базе, запущенный с `--gpus all`, корректно вернул `torch.cuda.is_available() == True` и распознал GPU хоста.

Передача GPU в обычный `docker run`/контейнер Kubernetes всё равно требует `nvidia-container-toolkit` на хосте:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Проверка, что сработало: `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` должен напечатать твою видеокарту. В Kubernetes планирование GPU дополнительно требует наличия в кластере NVIDIA device plugin. `minikube start --gpus=all` устанавливает и настраивает его автоматически; без него поды `api`, `worker` и `ollama` (каждый запрашивает `nvidia.com/gpu: 1`) остаются в `Pending` с событием `Insufficient nvidia.com/gpu`. `EMBEDDING_DEVICE=cuda` требует, чтобы воркер работал с пулом Celery `--pool=solo` (не дефолтным prefork), так как torch запрещает повторную инициализацию CUDA внутри форкнутого процесса. Deployment воркера в `k8s/worker.yaml` уже переопределяет команду по этой причине.

**На машине с одной видеокартой** device plugin объявляет ровно один `nvidia.com/gpu`, и Kubernetes относится к нему как к эксклюзивному, неделимому ресурсу, в отличие от `docker run --gpus all`, который позволяет любому числу контейнеров свободно делить одну физическую видеокарту. Поэтому `api`, `worker` и `ollama` (каждый запрашивает одну GPU) не могут одновременно работать на одноGPU-ноде: те два, что проиграли гонку за планирование, остаются в `Pending` с `Insufficient nvidia.com/gpu`, и это корректное поведение, а не баг. Проверено напрямую: скейл одного Deployment в `0` освобождает GPU, и следующий ожидающий под планируется на неё в течение секунд.

## Kubernetes

Обычные манифесты (без Helm) в `k8s/`, покрывающие весь стек, каждую инфраструктурную зависимость плюс API и воркер, в одном namespace `kip`: `StatefulSet` с `volumeClaimTemplates` для четырёх компонентов, где потеря данных при перезапуске была бы болезненной (`postgres`, `minio`, `elasticsearch`, кеш модели `ollama`), обычные `Deployment` для всего остального, `ConfigMap` (`kip-config`) для несекретных переменных окружения, указывающих на внутрикластерные DNS-имена (`postgres.kip.svc.cluster.local` и т.д.), и один `Secret` (`kip-secrets`), закоммиченный с плейсхолдер/дев-значениями. Заполни реальными значениями перед применением где-либо, кроме локального кластера.

```bash
docker build -t kip:latest .
# загрузи локально собранный образ в кластер, точная команда зависит от инструмента:
kind load docker-image kip:latest --name <cluster-name>        # kind
minikube image load kip:latest                                  # minikube

# заполни реальные значения в k8s/secret.yaml перед применением где-либо, кроме локального кластера
kubectl apply -f k8s/
kubectl get pods -n kip
```

Реестр образов не используется: образ `api`/`worker` собирается локально и загружается прямо в кластер (`imagePullPolicy: IfNotPresent`), что соответствует тому, что это демо/локальный деплой, а не managed-кластер.

**Проверено живьём** на локальном кластере `minikube --driver=docker --gpus=all`: `kubectl apply -f k8s/` поднимает каждый ресурс в namespace `kip`, все девять инфраструктурных подов (`postgres`, `rabbitmq`, `redis`, `minio`, `elasticsearch`, `ollama`, `tempo`, `prometheus`, `grafana`) доходят до `Running`, а (после освобождения единственной GPU ноды, см. заметку выше) сам `api` доходит до `Running`, подтверждает `torch.cuda.is_available() == True` внутри пода и отвечает на `GET /health` строкой `{"status":"ok"}` через `kubectl port-forward`. Это помогло найти и исправить один реальный баг: `minio.yaml` использовал `command:` для передачи CLI-флагов MinIO, но в Kubernetes (в отличие от Docker Compose) `command:` заменяет *entrypoint* образа, а не только его аргументы по умолчанию. Нужен был `args:` вместо этого, чтобы сохранить собственный entrypoint `minio` образа и просто передать ему `server /data --console-address :9091`.

## Документация API

Интерактивная документация автогенерируется FastAPI на `http://localhost:8000/docs`, пока сервер запущен. Статический экспорт той же схемы, сгенерированный прямо из `app.openapi()`, закоммичен в [`docs/openapi.json`](docs/openapi.json) для просмотра без запуска сервера.

Пример запроса:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "longenoughpassword"}'
```

## Миграции базы данных

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

## Тесты

```bash
uv run pytest -v                        # всё
uv run pytest -v -m "not integration"   # быстрый цикл, без Docker
uv run pytest -v -m integration         # только тесты на Testcontainers
```

Юнит-тесты (сервисный слой, против in-memory фейковых репозиториев) и интеграционные тесты (репозитории и полные API-флоу, против настоящих контейнеров Postgres, Elasticsearch, MinIO и Redis через Testcontainers) лежат рядом друг с другом под `tests/`, повторяя структуру слоёв `src/`. Пайплайн загрузки дополнительно имеет оркестрационный тест против фейков (`tests/presentation/tasks/test_ingestion.py`) и полный end-to-end тест против настоящей инфраструктуры (`tests/presentation/tasks/test_ingestion_integration.py`); у Search есть аналогичный end-to-end тест против реального результата пайплайна (`tests/presentation/api/search/test_search_integration.py`); у Conversations/RAG есть аналогичный против настоящих Postgres и Elasticsearch, с LLM, всегда подменённой фейком (`tests/presentation/api/conversations/test_rag_integration.py`). У Observability свои прицельные тесты: rate limiting на Redis против настоящего Redis (Testcontainers), форматирование JSON-логов и инъекция контекста трейса, трассировка (через `InMemorySpanExporter` OpenTelemetry, без настоящего Tempo), кастомные гистограммы Prometheus и поведение перехвата Sentry (замоканное, никогда настоящий сетевой вызов).

Тесты, которым нужна настоящая инфраструктура (Postgres, Elasticsearch, MinIO, Redis, через Testcontainers), помечены `@pytest.mark.integration` (124 быстрых / 50 интеграционных из 174 всего); всё остальное вообще не требует Docker.

## Continuous Integration

`.github/workflows/ci.yml` запускается на каждый push/PR в `main`: job `lint` (Ruff, mypy strict) и job `test` (полный набор тестов, включая тесты на Testcontainers; у GitHub-хостед раннеров уже есть Docker). В CI не собирается и не пушится Docker-образ, это остаётся ручным шагом.

## Ограничения

- Пока нет настоящей доставки email: токены верификации логируются, а не отправляются.
- Нет флоу сброса пароля.
- Только типы источников PDF и Markdown; Web и Git станут будущими добавлениями в виде Strategy.
- Один провайдер эмбеддингов "активен" на деплой; переключение требует переэмбеддинга всего корпуса.
- У поиска нет пагинации: один ранжированный список, ограниченный 50 результатами.
- Нет подсветки сниппетов: каждый результат возвращает весь (короткий) текст чанка.
- У диалогов нет заголовков, их нельзя переименовать.
- Нет управления контекстным окном: вся история сообщений отправляется в LLM на каждом ходе; очень длинные диалоги в итоге упрутся в лимит контекста модели.
- Нет повтора или фолбэка между LLM-провайдерами: один активен на деплой (`LLM_PROVIDER`).
- Rate limiting фиксирован (не настраивается) и применяется только к `/auth/login`, `/auth/register`, `/auth/refresh`, по ключу client IP.
- Нет агрегации логов (Loki): логи пишутся в JSON в stdout, смотреть через `docker compose logs` или терминал запущенного процесса.
- Не настроены правила алертинга в Prometheus или Grafana.
- Мониторинг производительности/профилирование Sentry отключены; только перехват ошибок.
- На машине с одной видеокартой только один из `api`/`worker`/`ollama` может держать единственную `nvidia.com/gpu` ноды одновременно; два других остаются в `Pending`, пока она не освободится (см. "Поддержка GPU"). Не проблема на мультиGPU или CPU-only (`EMBEDDING_DEVICE=cpu`) деплое.
- Манифесты Kubernetes не протестированы против настоящего managed-кластера (EKS/GKE/AKS), только против локального кластера `minikube`.
- Нет автоматизации реестра образов/push: сборка и загрузка образа в кластер остаются ручным шагом.
- Workflow GitHub Actions написан и провалидирован как YAML, но не проверен end-to-end: в этом репозитории не настроен remote, так что он ещё никогда реально не запускался. Запустится при первом push этого репозитория на GitHub.

## Лицензия

MIT, согласно `pyproject.toml`.
