# Python FastAPI Service Architecture

Reference architecture for all Python microservices in Memosphere (e.g. `question-generation-service`). Async-first, layered, dependency-injected — built on FastAPI + Pydantic v2 + SQLAlchemy 2.0 async.

## Layers

| Layer            | Responsibility                                                                                                                                                           | Depends on         |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ |
| **Router**       | HTTP I/O only: parse request, call service, return response model. No business logic, no SQL.                                                                            | Service (via DI)   |
| **Schema**       | Pydantic models for request/response validation (I/O shape).                                                                                                             | Nothing            |
| **Service**      | Business logic / use cases. Orchestrates repositories and clients.                                                                                                       | Repository, Client |
| **Repository**   | All DB access (queries, inserts) for one aggregate/table. Hides SQLAlchemy from the service.                                                                             | Model, DB session  |
| **Client**       | Wraps one external API/SDK (AI provider, third-party service). Hides HTTP/SDK details — auth, retries, payload shaping — and translates failures into domain exceptions. | Core (settings)    |
| **Model**        | SQLAlchemy ORM table definitions (persistence shape, not I/O shape).                                                                                                     | Nothing            |
| **Core**         | Settings, app config, cross-cutting concerns (logging, security, domain exceptions).                                                                                     | Nothing            |
| **Dependencies** | FastAPI `Depends()` wiring — builds services/repositories/clients with their dependencies injected.                                                                      | Everything above   |

**Rule:** Pydantic schemas (I/O) and SQLAlchemy models (persistence) are never the same class. Routers never import a repository, client, or the DB session directly — only services do, and only through DI.

A **Client** is the external-API analogue of a Repository: a Repository hides SQLAlchemy behind domain methods, a Client hides an SDK/HTTP call the same way. `ai/mistral.py` is this layer's first instance — formalize new third-party integrations as `clients/<provider>_client.py` rather than scattering raw SDK calls in services.

## Folder Structure

```
src/<service_name>/
├── main.py                  # FastAPI app instance, router registration
├── core/
│   └── config.py            # Settings (pydantic-settings, env vars)
├── routers/
│   └── <resource>_router.py # HTTP endpoints
├── schemas/
│   └── <resource>.py        # Pydantic request/response models
├── services/
│   └── <resource>_service.py # Business logic
├── repositories/
│   └── <resource>_repository.py # DB queries
├── clients/
│   └── <provider>_client.py # External API/SDK wrappers (e.g. ai/mistral.py)
├── models/
│   └── <resource>.py        # SQLAlchemy ORM models
├── dependencies/
│   └── services.py          # Depends() providers (DI wiring)
└── db/
    ├── session.py           # Async engine + session factory
    └── unit_of_work.py      # Multi-repository transaction boundary
```

## Request Flow (Mermaid)

Sources: [`diagrams/python-fastapi-sequence.mmd`](diagrams/python-fastapi-sequence.mmd) · [`diagrams/python-fastapi-flow.mmd`](diagrams/python-fastapi-flow.mmd)

## Examples

### 1. Schema (`schemas/thema.py`)

```python
from pydantic import BaseModel, Field


class ThemaRequest(BaseModel):
    raw_user_input: str = Field(min_length=2, max_length=10000)


class ThemaResponse(BaseModel):
    thema: str
    topics: list[str]
    raw_user_input: str
```

### 2. Model (`models/thema.py`)

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from question_generation_service.db.base import Base


class ThemaExtractionInput(Base):
    __tablename__ = "thema_extraction_inputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    raw_user_input: Mapped[str] = mapped_column(String(10000))
    thema: Mapped[str] = mapped_column(String(255))
```

### 3. Repository (`repositories/thema_repository.py`)

```python
from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.thema import ThemaExtractionInput


class ThemaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, raw_user_input: str, thema: str) -> ThemaExtractionInput:
        entry = ThemaExtractionInput(raw_user_input=raw_user_input, thema=thema)
        self.session.add(entry)
        await self.session.commit()
        return entry
```

### 4. Service (`services/thema_service.py`)

```python
from question_generation_service.repositories.thema_repository import ThemaRepository
from question_generation_service.schemas.thema import ThemaResponse
from question_generation_service.ai.mistral import mistral_req
from question_generation_service.prompts.thema_topic_extract import (
    PROMPT_1_SYSTEM,
    PROMPT_1_CONFIG,
)


class ThemaService:
    def __init__(self, repository: ThemaRepository):
        self.repository = repository

    async def extract_thema_topic_from_raw_input(self, raw_user_input: str) -> ThemaResponse:
        result = await mistral_req(
            system_msg=PROMPT_1_SYSTEM, user_msg=raw_user_input, config=PROMPT_1_CONFIG
        )
        await self.repository.save(raw_user_input, result["thema"])
        return ThemaResponse(raw_user_input=raw_user_input, **result)
```

### 5. Dependencies (`dependencies/services.py`)

```python
from typing import Annotated
from fastapi import Depends

from question_generation_service.db.session import SessionDep
from question_generation_service.repositories.thema_repository import ThemaRepository
from question_generation_service.services.thema_service import ThemaService


def get_thema_repository(session: SessionDep) -> ThemaRepository:
    return ThemaRepository(session)


def get_thema_service(
    repository: Annotated[ThemaRepository, Depends(get_thema_repository)]
) -> ThemaService:
    return ThemaService(repository)


ThemaServiceDep = Annotated[ThemaService, Depends(get_thema_service)]
```

### 6. Router (`routers/thema_router.py`)

```python
from fastapi import APIRouter

from question_generation_service.dependencies.services import ThemaServiceDep
from question_generation_service.schemas.thema import ThemaRequest, ThemaResponse

thema_router = APIRouter(prefix="/v1/thema", tags=["Thema & Topics"])


@thema_router.post("/", response_model=ThemaResponse)
async def extract_thema_topics(service: ThemaServiceDep, body: ThemaRequest):
    return await service.extract_thema_topic_from_raw_input(body.raw_user_input)
```

### 7. Core Config (`core/config.py`)

```python
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str
    MISTRAL_API_KEY: str
    DEBUG: bool = False

    model_config = SettingsConfigDict(env_file=str(ENV_PATH), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`get_settings()` is cached (one instance per process) and import-free of side effects — modules call it at the point of use instead of relying on a module-level `settings` singleton built at import time. This also makes settings overridable in tests via `app.dependency_overrides[get_settings]`, and removes the need for a `# type: ignore[call-arg]` workaround.

### 8. DB Session (`db/session.py`)

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from question_generation_service.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    url=settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
)

# Built once at module import — never recreate this inside a request-scoped function.
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
```

The engine is created once at import, but it still owns a connection pool that must be closed on shutdown — that's a `lifespan`, not a teardown left to the OS:

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

from question_generation_service.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
```

**Rule:** any resource with a pool/connection to release (DB engine, AI provider's `httpx`/SDK client) is opened once at import and closed in `lifespan`'s shutdown phase. `@app.on_event("startup"/"shutdown")` is deprecated — `lifespan` is the only supported hook.

### 9. Client (`clients/mistral_client.py`)

```python
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from question_generation_service.core.config import get_settings
from question_generation_service.core.exceptions import AIUnavailableError

settings = get_settings()


@retry(
    retry=retry_if_exception_type(AIUnavailableError),
    wait=wait_exponential(multiplier=0.5, max=8),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def chat_complete(system_msg: str, user_msg: str) -> dict:
    try:
        response = await mistral_sdk_call(api_key=settings.MISTRAL_API_KEY, ...)
    except SDKError as e:
        raise AIUnavailableError(f"Mistral API returned {e.status_code}") from e
    return response
```

The Client is the only place that imports the third-party SDK. Services call `chat_complete(...)`, never the SDK directly — this is what makes the AI provider mockable in service-level tests and swappable without touching business logic.

**Rule:** retries on transient upstream failures (timeouts, 429/5xx) belong on the Client, via `tenacity` — never hand-rolled `for attempt in range(...)` loops, and never retried again one layer up in the Service.

### 10. Domain Exceptions & Error Handling (`core/exceptions.py`, `main.py`)

```python
# core/exceptions.py
class DomainError(Exception):
    """Base class for all business/domain exceptions."""


class NotFoundError(DomainError):
    """Requested resource does not exist."""


class AIUnavailableError(DomainError):
    """Upstream AI provider unreachable or erroring."""
```

```python
# main.py
from fastapi import Request
from fastapi.responses import JSONResponse

from question_generation_service.core.exceptions import DomainError, NotFoundError, AIUnavailableError

_STATUS_BY_EXCEPTION = {
    NotFoundError: 404,
    AIUnavailableError: 503,
}


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    status_code = _STATUS_BY_EXCEPTION.get(type(exc), 400)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})
```

**Rule:** Services and Clients raise `DomainError` subclasses, never `HTTPException`. Routers stay free of `try`/`except` — only `main.py`'s exception handlers know about HTTP status codes.

### 11. Auth Dependency (`dependencies/auth.py`)

```python
from fastapi import Depends, Header, HTTPException, status

from question_generation_service.core.config import get_settings, Settings


async def verify_service_api_key(
    x_api_key: str = Header(...),
    settings: Settings = Depends(get_settings),
) -> None:
    if x_api_key != settings.SERVICE_API_KEY:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")


RequireServiceAuth = Depends(verify_service_api_key)
```

Service-to-service calls (e.g. behind an internal gateway) use an API-key dependency like this; swap for `OAuth2PasswordBearer`/JWT if the endpoint is user-facing. Either way, auth is a `Depends()` on the router — never logic embedded in the service.

## Transactions & Unit of Work

The `ThemaRepository.save()` example above commits internally — that only works because the service touches **one** repository. The moment a service must write to two or more repositories atomically, move commit ownership up into a `UnitOfWork`:

```python
# db/unit_of_work.py
from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.repositories.thema_repository import ThemaRepository
from question_generation_service.repositories.topic_repository import TopicRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.thema = ThemaRepository(session)
        self.topics = TopicRepository(session)

    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            await self.session.rollback()
```

```python
# services/thema_service.py
class ThemaService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def extract_and_link(self, raw_user_input: str) -> ThemaResponse:
        result = await mistral_req(...)
        async with self.uow as uow:
            thema = await uow.thema.add(raw_user_input, result["thema"])
            await uow.topics.add_many(thema.id, result["topics"])
            await uow.session.commit()  # one commit for both writes
        return ThemaResponse(raw_user_input=raw_user_input, **result)
```

**Rule:** a repository used through a `UnitOfWork` never calls `commit()` itself — only `add()`/query methods. A repository may still commit on its own behalf in the single-repository case (as in the earlier example), but switch to a `UnitOfWork` as soon as a second repository joins the transaction.

## Conventions

- **Async everywhere**: all I/O (DB, HTTP calls to AI providers) is `async def` — never block the event loop.
- **DI over imports**: services/repositories are built via `Depends()`, never instantiated directly inside a router.
- **One repository per aggregate**: keep SQL queries colocated with the table they touch.
- **Settings via `pydantic-settings`**: no `os.getenv` scattered in code — one `Settings` class per service.
- **Versioned routes**: prefix routers with `/v1/...` so breaking changes can coexist with `/v2/...`.
- **Start simple**: a tiny service can skip `repositories/` and let the service use `SessionDep` directly — add the repository layer once queries start repeating or routers exceed a few hundred lines.
- **Commit ownership**: a repository commits only in the single-repository case; once a service needs two or more repositories in one transaction, commit moves to a `UnitOfWork` (see above) and repositories only `add()`/query.
- **Domain exceptions over `HTTPException`**: services and clients raise `DomainError` subclasses; only the global exception handlers in `main.py` map them to HTTP status codes.
- **One client per integration**: third-party SDK calls live in `clients/`, never inline in a service — same logic as "one repository per aggregate."
- **Lifespan over `on_event`**: anything opened once at import (DB engine, AI SDK's HTTP client) is closed in `lifespan`'s shutdown phase; `@app.on_event("startup"/"shutdown")` is deprecated.
- **Retries via `tenacity`, on the Client**: never hand-rolled retry loops, and never retried again one layer up in the Service.

## Testing

- Override `SessionDep` with a transactional test session via `app.dependency_overrides` — never hit the real database from unit tests.
- For Repository/integration tests that need a real database, use **testcontainers-python** (`testcontainers[postgres]`) to spin up an ephemeral, disposable Postgres per test session — not a hand-run Docker container or SQLite (SQLite's dialect drifts from Postgres-specific SQL/types and hides bugs that only show up against the real engine).
- Override `get_settings` the same way to inject test config (fake API keys, test DB URL).
- Unit-test Services with fake Repository/Client doubles; reserve real-DB integration tests for the Repository layer itself.
- Use `pytest-asyncio` (or `anyio`) for all async test functions, matching the service's async-everywhere convention.

## Migrations

- Schema changes go through **Alembic** — `alembic revision --autogenerate -m "<change>"`, reviewed, then `alembic upgrade head`.
- Every new/changed `models/*.py` class needs a corresponding migration in the same PR; never apply schema changes by hand against a running DB.

## Observability

- **OpenTelemetry** is the default for traces, metrics, and logs together — not Prometheus scraping in isolation. `opentelemetry-instrumentation-fastapi` + `opentelemetry-instrumentation-sqlalchemy` auto-instrument the Router/DB layers; export via OTLP to whatever backend the platform uses (collector, Tempo/Jaeger, etc.).
- **AI calls get their own spans**, instrumented in the Client layer (never the Service), following the [GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — attributes for model name, input/output token counts, and latency per call. This is what makes per-request LLM cost and latency queryable instead of guessed at.
- Structured logging (e.g. `structlog` or stdlib `logging` with a JSON formatter) — never bare `print()`; logs carry the trace ID from the active OTel span so a request can be followed across logs, traces, and metrics.
- Health endpoint (`/health`) for liveness/readiness probes; keep it dependency-free (no DB/AI calls) so it can't false-negative on an unrelated outage.

Sources:

- [FastAPI official docs — Bigger Applications / Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [full-stack-fastapi-template (tiangolo, GitHub)](https://github.com/tiangolo/full-stack-fastapi-template)
- [zhanymkanov/fastapi-best-practices (GitHub)](https://github.com/zhanymkanov/fastapi-best-practices)
- [Architecture Patterns with Python — "Cosmic Python" (Repository & Unit of Work patterns)](https://www.cosmicpython.com/book/preface.html)
- [fastapi-best-architecture (GitHub)](https://github.com/fastapi-practices/fastapi-best-architecture)
