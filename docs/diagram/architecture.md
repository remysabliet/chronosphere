# Memosphere Architecture Diagrams

Two diagrams, kept deliberately separate so "what's real" is never mixed with "what's planned":

1. **[System architecture](#1-system-architecture-current-state)** — what the code actually does today.
2. **[Deployment target](#2-deployment-target-planned)** — the AWS topology described in [infra-architecture.md](../architecture/infra-architecture.md), not yet provisioned.

## 1. System architecture (current state)

Source: [`system-architecture.mmd`](system-architecture.mmd)

Only **question-generation-service** (FastAPI) is fully built — it owns thema extraction, the
wizard, quiz creation, quiz sessions/answers, question generation, and moderation. Everything a
learner does today flows through it. Six other services (`user-management`, `content-management`,
`quiz-session`, `analytics`, `notification`, `learning-engine`) exist in `docker-compose.yml` and
`nginx.conf` but only expose a `/health` stub — shown dashed/grey below. The `nginx` gateway is
running and correctly configured for all seven services, but `web-app` currently calls
question-generation-service directly (via `NEXT_PUBLIC_QUESTION_GEN_URL`), so the gateway sits
unused on the one real request path.

The most important detail is the async question-generation pipeline: `POST /v1/quizzes` writes the
quiz row and its outbox events in one Postgres transaction; a background `OutboxRelay` task
publishes those events to a Redis stream; a background `GenerationWorker` task consumes the stream,
calls Mistral, and writes the generated questions back to Postgres. Both workers run in-process
inside the question-generation-service, not as separate deployables.

```mermaid
flowchart TB
    Learner(["Learner / Admin / Moderator"])

    subgraph Client["Client"]
        WebApp["web-app<br/>Next.js + NextAuth"]
    end

    Cognito["Amazon Cognito<br/>Hosted UI / OIDC (live)"]

    subgraph Edge["Edge — nginx (docker-compose)"]
        Gateway["NGINX Gateway<br/>routes /api/* per nginx.conf"]
    end

    subgraph QGS["question-generation-service — FastAPI :8001 (the one fully-built backend)"]
        Routers["HTTP routers<br/>thema / wizard / concept /<br/>quiz / session / questions / moderation"]
        QuizSvc["QuizService.create()"]
        SessionSvc["SessionService"]
        Relay["OutboxRelay<br/>background asyncio task"]
        Worker["GenerationWorker<br/>background asyncio task"]
    end

    Mistral["Mistral Large API<br/>(live, external)"]

    subgraph Data["Data Layer (docker-compose containers)"]
        Postgres[("PostgreSQL<br/>quizzes, outbox, questions,<br/>learning_units, sessions, users...")]
        Redis[("Redis Streams<br/>topic: jobs:generate-questions")]
    end

    Migration["migration-service<br/>one-shot job, runs before app services"]

    subgraph Stubs["Scaffolded services — health-check only, no business logic yet"]
        UserMgmt["user-management-service<br/>NestJS :3001"]
        ContentMgmt["content-management-service<br/>NestJS :3002"]
        QuizSession["quiz-session-service<br/>NestJS :3003"]
        Analytics["analytics-service<br/>NestJS :3004"]
        Notification["notification-service<br/>NestJS :3005"]
        LearningEngine["learning-engine-service<br/>FastAPI :8002 — BKT/IRT TODO"]
    end

    Learner --> WebApp
    WebApp -- "1: OAuth2/OIDC login" --> Cognito
    Cognito -- "2: ID token + refresh token" --> WebApp
    WebApp -- "3: server actions, Bearer idToken<br/>(calls :8001 directly, bypasses Gateway)" --> Routers
    Routers -. "verifies JWT via cached JWKS" .-> Cognito

    WebApp -. "configured route, unused by real traffic" .-> Gateway
    Gateway -. "nginx.conf upstreams" .-> UserMgmt
    Gateway -. "nginx.conf upstreams" .-> ContentMgmt
    Gateway -. "nginx.conf upstreams" .-> QuizSession
    Gateway -. "nginx.conf upstreams" .-> Analytics
    Gateway -. "nginx.conf upstreams" .-> Notification
    Gateway -. "nginx.conf upstreams" .-> LearningEngine
    Gateway -. "nginx.conf upstreams" .-> Routers

    Routers --> QuizSvc
    Routers --> SessionSvc

    QuizSvc -- "4: INSERT quiz + outbox row(s)<br/>same transaction" --> Postgres
    Relay -- "5: poll unpublished outbox rows" --> Postgres
    Relay -- "6: XADD jobs:generate-questions" --> Redis
    Worker -- "7: XREADGROUP (consumer group)" --> Redis
    Worker -- "8: generate + judge" --> Mistral
    Worker -- "9: store questions,<br/>increment quiz progress" --> Postgres

    SessionSvc -- "sessions, submitted answers" --> Postgres

    Migration -- "schema + seed" --> Postgres

    classDef stub stroke-dasharray: 4 4,fill:#eee,color:#666,stroke:#999;
    class UserMgmt,ContentMgmt,QuizSession,Analytics,Notification,LearningEngine stub;
```

## 2. Deployment target (planned)

Source: [`deployment-target.mmd`](deployment-target.mmd)

This is the AWS topology described in [infra-architecture.md](../architecture/infra-architecture.md)
(Kubernetes on EC2, RDS, ElastiCache, S3, ECR, self-hosted Actions runner). None of it is
provisioned — there's no Terraform/IaC or k8s manifests in the repo, and
[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) currently only runs
lint/type-check/tests on GitHub-hosted runners. Cognito and Mistral are the two pieces of this
diagram that are already live, since the application code integrates them directly regardless of
where it's deployed.

```mermaid
flowchart TB
    Dev["Developer"] -- "git push" --> GitHub["GitHub<br/>(source control)"]

    subgraph CICD["CI/CD — planned"]
        Actions["GitHub Actions<br/>self-hosted runner on EC2"]
        ECR[("Amazon ECR<br/>private image registry")]
    end

    GitHub -- "triggers workflow" --> Actions
    Actions -- "build + push image" --> ECR

    subgraph AWS["AWS — planned target infra"]
        subgraph K8s["Kubernetes on EC2 (manual scaling)"]
            Gateway["NGINX Gateway"]
            Services["Application pods:<br/>web-app + all microservices<br/>(same topology as system-architecture.mmd)"]
            MigrationJob["migration-service<br/>(Job, runs on deploy)"]
        end
        RDS[("Amazon RDS PostgreSQL<br/>db.t4g.micro, Free Tier")]
        ElastiCache[("Amazon ElastiCache Redis<br/>optional for MVP")]
        S3[("Amazon S3<br/>object storage, Free Tier")]
        CognitoTarget["Amazon Cognito<br/>OAuth2 (already live today)"]
    end

    Mistral["Mistral Large API<br/>(external, already live today)"]

    Actions -- "kubectl / Helm apply" --> K8s
    ECR -- "pulled by" --> Services

    Gateway --> Services
    Services --> RDS
    Services -.-> ElastiCache
    Services --> CognitoTarget
    Services -- "question generation" --> Mistral
    Services -.-> S3
    MigrationJob --> RDS

    classDef planned stroke-dasharray: 4 4,fill:#eee,color:#666,stroke:#999;
    class Actions,ECR,Gateway,Services,MigrationJob,RDS,ElastiCache,S3 planned;
```
