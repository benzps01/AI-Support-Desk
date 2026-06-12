# AI Support Desk — Application Design Document

A full-stack helpdesk platform with an integrated AI triage-and-assist pipeline. Built as a portfolio project that demonstrates production full-stack engineering **and** applied LLM integration — the "Full-Stack AI Engineer" profile.

**Scope:** serious portfolio build, ~3–5 weeks, solo. Backend: FastAPI/Python. Frontend: React + Vite + JavaScript.

---

## 1. Problem & Goals

Support teams drown in incoming tickets. Triage (what is this, how urgent, who handles it) and first-response drafting are slow and manual. This app automates the boring parts so agents resolve faster.

**Goals**
- A working multi-role helpdesk: customers file tickets, agents resolve them, admins oversee.
- An AI layer that auto-classifies tickets, surfaces similar past resolutions, and drafts replies grounded in those resolutions (a mini-RAG inside the product).
- Real production concerns done properly: async processing, caching, real-time updates, auth, containerized local dev.

**Non-goals (deliberately parked — protect the timeline)**
- Billing / payments, true multi-tenant isolation (we scope by `org_id`, not separate DBs).
- Email/SMS channels (web-only intake for v1).
- Agentic auto-resolution, model fine-tuning, SSO. All go in the roadmap.

---

## 2. Core Features (by role)

**Customer**
- Register / log in; create a ticket (subject + body); view their tickets and the conversation thread.

**Agent**
- Live ticket queue with status, priority, SLA countdown; open a ticket and see the AI panel (category, priority, sentiment, *similar resolved tickets*, *suggested reply*); accept/edit/send the suggested reply; reassign, change status, add internal notes.

**Admin**
- Everything an agent can do, plus an analytics summary (open vs resolved, avg resolution time, AI suggestion acceptance rate) and user/role management.

---

## 3. System Architecture

Three deployable units plus two infra services. This is **service-oriented, not microservices sprawl** — and that restraint is intentional.

```mermaid
flowchart TB
    subgraph Client
        FE[React + Vite (JS)<br/>agent dashboard]
    end

    subgraph Backend
        API[Core API<br/>FastAPI async]
        WORKER[AI Worker<br/>Celery]
    end

    subgraph Infra
        PG[(PostgreSQL 16<br/>+ pgvector)]
        REDIS[(Redis 7<br/>cache · queue · pub/sub)]
        LLM[LLM provider<br/>local oMLX/Gemma in dev<br/>hosted API in prod]
    end

    FE -->|REST| API
    FE <-->|WebSocket| API
    API -->|read/write| PG
    API -->|cache + enqueue job| REDIS
    REDIS -->|deliver job| WORKER
    WORKER -->|classify · embed · suggest| LLM
    WORKER -->|write results| PG
    WORKER -->|publish event| REDIS
    REDIS -->|pub/sub fanout| API
    API -->|push update| FE
```

**Why the AI worker is split out (and nothing else is).** LLM calls take 1–5 seconds and scale on a completely different axis than CRUD. If they ran inside the API request, a handful of slow calls would starve your request workers and the UI would hang. Splitting *only* the AI work into an async worker is a real, defensible boundary. Splitting every entity into its own service would be over-engineering for this scope — modern practice reserves full microservices for genuine independent-scaling or large-team needs, which a solo portfolio app does not have. **This is a deliberate architecture decision you can defend in an interview**, which is worth more than an impressive-looking diagram.

---

## 4. Tech Stack (and why)

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | React + Vite + JavaScript, Tailwind, TanStack Query | Your stack; TanStack Query handles server-state caching + refetch cleanly |
| Core API | FastAPI (Python 3.11+), Pydantic v2, async | Fast, async, doubles as AI-stack practice |
| ORM / migrations | SQLAlchemy 2.0 (async) + Alembic | Standard, async-capable, real migration discipline |
| Task queue | Celery + Redis broker | Widely recognized; runs the async AI jobs. *(Arq is a lighter async-native alternative if you prefer modern fit over keyword recognition.)* |
| Database | PostgreSQL 16 + `pgvector` | One DB for relational **and** vector search — no separate vector DB needed |
| Cache / queue / pub-sub | Redis 7 | Caching, Celery broker, WebSocket fanout, rate limiting, semantic cache |
| Real-time | WebSockets + Redis pub/sub | Live queue updates; pub/sub bridges worker → API → browser |
| LLM | Provider API behind a swappable client; **local oMLX/Gemma-4 E4B in dev** | Zero-cost local dev (reuses your RAG setup), swap to hosted in prod |
| Embeddings | `nomic-embed-text-v1.5` → pgvector | Same embedding model you know; powers similar-ticket search |
| Containers | Docker + Docker Compose | One-command local stack; **not** K8s (over-engineering here, and consistent with your résumé) |
| Testing | pytest, Vitest, Playwright | Current 2026 defaults (Playwright over Selenium) |
| Auth | JWT (access + refresh), Argon2 hashing, RBAC | Standard, defensible |

---

## 5. Service Responsibilities

**Core API (FastAPI)** — auth, all CRUD, RBAC enforcement, read caching, enqueuing AI jobs, the WebSocket endpoint, and subscribing to Redis pub/sub to push results to clients. Never calls the LLM directly.

**AI Worker (Celery)** — consumes jobs from Redis. For each new ticket: classify → embed → find similar resolved tickets → draft a suggested reply → write results → publish an event. Owns all LLM/embedding calls and the swappable model client.

**Frontend (React/Vite)** — auth flows, ticket list/detail, the agent dashboard with the live queue and AI panel, admin analytics. Holds a WebSocket connection for live updates.

---

## 6. Data Model (PostgreSQL)

Core tables (key columns shown):

```
organizations(id, name, created_at)

users(id, org_id → organizations, email UNIQUE, password_hash,
      role ∈ {customer, agent, admin}, name, created_at)

tickets(id, org_id, customer_id → users, assigned_agent_id → users NULL,
        subject, body, status ∈ {open, in_progress, resolved, closed},
        priority ∈ {low, medium, high, urgent} NULL,   -- set by AI
        category TEXT NULL, sentiment TEXT NULL,         -- set by AI
        sla_due_at TIMESTAMP NULL,
        created_at, updated_at, resolved_at NULL)

ticket_messages(id, ticket_id → tickets, sender_id → users,
                body, is_internal_note BOOL, created_at)

ticket_embeddings(ticket_id → tickets PK, embedding vector(768))  -- pgvector

ai_suggestions(id, ticket_id → tickets, type ∈ {classification, reply},
               content JSONB, model TEXT, created_at,
               accepted BOOL NULL)   -- did the agent use it? = a real metric

sla_policies(id, org_id, priority, response_minutes, resolution_minutes)
```

`ticket_embeddings` uses a `pgvector` column with an HNSW or IVFFlat index for fast similarity search. `ai_suggestions.accepted` gives you a genuine product metric — *"agents accepted the AI's draft 62% of the time"* — which is a great line for both the README and an interview.

---

## 7. API Design

**REST (key endpoints)**
```
POST   /auth/register            POST /auth/login            POST /auth/refresh
POST   /tickets                  # create → enqueues AI job, returns immediately
GET    /tickets                  # list (filtered by role/org, cached)
GET    /tickets/{id}             # detail + thread
PATCH  /tickets/{id}             # status / assignment / priority
POST   /tickets/{id}/messages    # reply or internal note
GET    /tickets/{id}/similar     # pgvector top-k resolved tickets
POST   /tickets/{id}/accept-suggestion/{suggestion_id}
GET    /analytics/summary        # admin only, cached
```

**WebSocket** `/ws` (JWT-authenticated). Server → client events:
```
ticket.created     ticket.updated     ticket.assigned
message.created    ai.suggestion.ready
```

---

## 8. The AI Pipeline (the heart of the project)

Flow when a ticket is created:

1. **API** persists the ticket (`status=open`), enqueues a Celery job with `ticket_id`, and returns `201` instantly. The customer never waits on the LLM.
2. **Worker — classify.** One LLM call with a strict structured-output prompt → `{category, priority, sentiment}`. Validate the JSON with Pydantic (never trust raw LLM output); on failure, retry once then fall back to defaults. Update the ticket.
3. **Worker — embed.** Embed `subject + body` with `nomic-embed`; upsert into `ticket_embeddings`.
4. **Worker — retrieve similar.** pgvector query for the top-k **resolved** tickets in the same org. This is your retrieval step.
5. **Worker — suggest reply.** LLM call grounded in the current ticket **plus the similar resolved tickets as context** — a mini-RAG. Store the draft in `ai_suggestions`.
6. **Worker — publish.** Push `ai.suggestion.ready` to Redis pub/sub → API → WebSocket → the agent's dashboard updates live.

**Semantic cache (cost + latency win).** Before the suggest-reply call, check a Redis-backed semantic cache keyed by query-embedding similarity. If a near-identical question was answered recently, reuse the draft. This is the same technique from your RAG roadmap, now in a product.

**Guardrails (interviewers ask about these).**
- API keys live server-side only, never shipped to the browser.
- Structured-output validation on every LLM response.
- PII kept out of logs; redact before logging prompts.
- Per-user and per-org rate limiting on AI endpoints.
- Graceful degradation: if the LLM is down, tickets still work — they just lack AI enrichment.
- Provider abstraction: a `LLMClient` interface with `local` (oMLX/Gemma) and `hosted` implementations, swapped by config.

> **The narrative payoff:** the suggested-reply feature is literally retrieval-augmented generation embedded in a real product. This project *extends* your standalone RAG work into an applied, user-facing feature — a clean, honest story for the bridge identity.

---

## 9. Caching Strategy (Redis)

| Use | Pattern | Notes |
|---|---|---|
| Ticket lists / analytics | Cache-aside, short TTL (30–60s) | Invalidate on write via the same events that drive WebSocket updates |
| Sessions / refresh tokens | Redis store + blocklist | Enables logout / token revocation |
| Rate limiting | Token bucket per user + per org | Strictest on AI endpoints |
| Task queue | Celery broker + result backend | The async backbone |
| Pub/sub | Channels per org/agent | Fans WebSocket events across multiple API instances |
| Semantic cache | Embedding-keyed lookup | Cuts repeat LLM cost/latency |

Be ready to talk about **cache invalidation**: you're using event-driven invalidation (a `ticket.updated` event both pushes the WebSocket update *and* busts the relevant cache keys), with TTLs as a safety net. That tradeoff discussion is exactly the kind of thing that separates a senior answer from a junior one.

---

## 10. Real-time, Auth & Security

**Real-time.** The browser opens an authenticated WebSocket; the API subscribes that connection to its org/agent channels. Because the AI result is produced in a *separate* worker, Redis pub/sub is what carries it back: worker publishes → every API instance subscribed to that channel receives it → pushes to the right clients. This is why pub/sub (not just an in-process event) is necessary.

**Auth & security.** JWT access + refresh tokens; Argon2 password hashing; a FastAPI dependency enforces RBAC per route; Pydantic validates all input; CORS locked to your frontend origin; secrets via env/`.env` (never committed). The AI-specific items from §8 stack on top.

---

## 11. Docker & Local Dev

`docker-compose.yml` services:
```
frontend   # vite dev server
api        # FastAPI (uvicorn)
worker     # celery worker
postgres   # pgvector/pgvector:pg16 image
redis      # redis:7
```
Plus healthchecks, named volumes for Postgres/Redis, and a shared `.env`. **Dev against your local Gemma-4 E4B via oMLX/Ollama** so you burn zero API credits while building; flip a config flag to a hosted model when you want to demo. `docker compose up` brings the whole stack online with one command.

---

## 12. Phased Build Plan (3–5 weeks, milestone-driven)

**Week 1 — Foundation & core CRUD (no AI yet).**
Repo + Docker Compose (postgres, redis, api, frontend skeleton). Auth: register/login/JWT/refresh/RBAC. Models + Alembic migrations for users/tickets/messages. Ticket CRUD endpoints + a minimal React UI to create/list/view tickets and post messages.
*Milestone: a working, non-AI helpdesk you can click through.*

**Week 2 — Async + AI classification.**
Add Celery + Redis broker + worker. On ticket create, enqueue a job. Worker calls the LLM for `{category, priority, sentiment}` with structured output + validation; build the swappable `LLMClient` (local Gemma in dev). Persist results.
*Milestone: new tickets get auto-triaged within a second or two.*

**Week 3 — Embeddings, similar tickets, suggested replies (mini-RAG).**
Enable pgvector; embed tickets; `/tickets/{id}/similar`. Add the suggest-reply job grounded in similar resolved tickets; `ai_suggestions` table; agent accept/edit flow.
*Milestone: the AI drafts replies grounded in your own past resolutions.*

**Week 4 — Real-time + caching + dashboard polish.**
WebSocket live updates (new ticket, assignment, `ai.suggestion.ready`) via Redis pub/sub. Redis read caching + event-driven invalidation. Rate limiting. Semantic cache for AI. Build the real agent dashboard: live queue, priority/SLA badges, the AI panel.
*Milestone: it feels like a real product.*

**Week 5 — Analytics, tests, deploy, docs (buffer).**
Admin analytics summary (cached). pytest for the API, Vitest for components, one Playwright happy-path (create ticket → AI triage → agent reply). Security hardening pass. Write the README with the architecture diagram. Optional: deploy to a cheap VM or Railway.
*Milestone: portfolio-ready, tested, documented.*

**If you only have 3 weeks:** do Weeks 1–3, fold a light version of real-time + caching into Week 3, and skip analytics + e2e. You still have an AI-integrated full-stack app that tells the whole story.

---

## 13. Roadmap (park these — talk about them, don't build them yet)

Email intake channel · true multi-tenancy · agentic auto-resolution (LLM resolves simple tickets end-to-end) · CSAT surveys · Langfuse observability on the AI calls · CI quality gate · knowledge-base articles as an additional retrieval source. Listing these in your README signals you know where the product goes without blowing your timeline.

---

## 14. Why this is résumé-worthy

Once shipped, this earns a bullet like:

> *Built an AI-integrated support platform (FastAPI, React, PostgreSQL/pgvector, Redis, Celery, Docker) — async LLM pipeline that auto-classifies tickets and drafts replies grounded in similar past resolutions (retrieval-augmented), with WebSocket real-time updates and a Redis caching/queue layer.*

And it hands you a set of interview talking points you can defend because you *built* them: why the AI worker is a justified service boundary, the cache-invalidation tradeoff, the LLM guardrails (structured output, fallback, rate limiting, key safety), the provider abstraction, and the mini-RAG feature that connects straight back to your standalone RAG project.

---

*Next step: when you're ready to start Week 1, I can scaffold the repo structure, the Docker Compose file, and the initial FastAPI + models, then we build it phase by phase.*
