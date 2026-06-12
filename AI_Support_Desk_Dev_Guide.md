# AI Support Desk — Phase-by-Phase Development Guide

Your week-by-week build reference. Each phase has a clear **goal**, a **task list**, the **new dependencies**, the **database changes**, and a **Definition of Done** you can check yourself against before moving on. Build in order — each week stacks on the last and ends in something you can demo.

**Stack:** React + Vite (JavaScript/JSX) frontend · FastAPI/Python backend · PostgreSQL 16 + pgvector · Redis 7 · Celery · Docker Compose. Develop the LLM/embedding calls against your **local Gemma-4 E4B + nomic-embed** (via Ollama/oMLX) so you spend nothing while building.

---

## 0. Prerequisites (one-time)

Install: Python 3.11+, Node 18+, Docker Desktop, Git, and your local model server (Ollama or oMLX) with `gemma4:e4b` and `nomic-embed-text` pulled. A Postgres GUI (TablePlus/DBeaver) is handy but optional.

Golden rule for the whole build: **commit at every Definition of Done.** Each phase below ends with a suggested commit message.

---

## 1. Target Folder Structure (the end state)

This is where you're headed. You'll create pieces of it week by week — don't scaffold all of it on day one.

```
ai-support-desk/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
│
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/                 # migration files land here
│   ├── app/
│   │   ├── main.py                   # FastAPI app, router includes, WS mount
│   │   ├── config.py                 # pydantic-settings (reads .env)
│   │   ├── db.py                     # async engine + session factory
│   │   ├── deps.py                   # get_db, get_current_user, require_role
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── organization.py
│   │   │   ├── user.py
│   │   │   ├── ticket.py
│   │   │   ├── message.py
│   │   │   ├── suggestion.py
│   │   │   └── embedding.py
│   │   ├── schemas/                  # Pydantic request/response models
│   │   │   ├── auth.py
│   │   │   ├── ticket.py
│   │   │   ├── message.py
│   │   │   └── analytics.py
│   │   ├── api/                      # routers
│   │   │   ├── auth.py
│   │   │   ├── tickets.py
│   │   │   ├── messages.py
│   │   │   ├── analytics.py
│   │   │   └── ws.py                 # WebSocket endpoint
│   │   ├── core/
│   │   │   ├── security.py           # JWT create/verify, password hashing
│   │   │   ├── cache.py              # Redis cache-aside helpers
│   │   │   ├── ratelimit.py          # token-bucket limiter
│   │   │   └── events.py             # Redis pub/sub publish + subscribe
│   │   ├── services/                 # business logic (keep routers thin)
│   │   │   ├── ticket_service.py
│   │   │   └── analytics_service.py
│   │   └── ai/
│   │       ├── client.py             # LLMClient interface + local/hosted impls
│   │       ├── embeddings.py         # embed text via nomic-embed
│   │       ├── classify.py           # classification logic
│   │       ├── suggest.py            # reply suggestion (mini-RAG)
│   │       ├── semantic_cache.py
│   │       └── prompts.py            # all prompt templates in one place
│   ├── worker/
│   │   ├── celery_app.py             # Celery instance (Redis broker)
│   │   └── tasks.py                  # process_new_ticket, etc.
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_tickets.py
│       └── test_ai_tasks.py
│
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx                   # routes
        ├── api/
        │   ├── client.js             # axios instance + interceptors
        │   └── hooks.js              # TanStack Query hooks
        ├── context/
        │   └── AuthContext.jsx
        ├── hooks/
        │   └── useWebSocket.js
        ├── components/
        │   ├── TicketCard.jsx
        │   ├── AiPanel.jsx
        │   └── ...
        ├── pages/
        │   ├── Login.jsx
        │   ├── Register.jsx
        │   ├── Tickets.jsx
        │   ├── TicketDetail.jsx
        │   └── Dashboard.jsx
        └── lib/
            └── format.js
```

---

## 2. Database Reference

Full schema (this is the *end state* — you'll add tables phase by phase via Alembic migrations, but keep this as your map). Vector dimension is **768** to match `nomic-embed-text-v1.5`.

```sql
CREATE EXTENSION IF NOT EXISTS vector;          -- added in Week 3

CREATE TABLE organizations (
  id          BIGSERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id            BIGSERIAL PRIMARY KEY,
  org_id        BIGINT NOT NULL REFERENCES organizations(id),
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('customer','agent','admin')),
  name          TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tickets (
  id                BIGSERIAL PRIMARY KEY,
  org_id            BIGINT NOT NULL REFERENCES organizations(id),
  customer_id       BIGINT NOT NULL REFERENCES users(id),
  assigned_agent_id BIGINT REFERENCES users(id),
  subject           TEXT NOT NULL,
  body              TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'open'
                      CHECK (status IN ('open','in_progress','resolved','closed')),
  priority          TEXT CHECK (priority IN ('low','medium','high','urgent')),  -- set by AI
  category          TEXT,                                                       -- set by AI
  sentiment         TEXT,                                                       -- set by AI
  sla_due_at        TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at       TIMESTAMPTZ
);
CREATE INDEX idx_tickets_org_status ON tickets(org_id, status);
CREATE INDEX idx_tickets_agent      ON tickets(assigned_agent_id);

CREATE TABLE ticket_messages (
  id               BIGSERIAL PRIMARY KEY,
  ticket_id        BIGINT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  sender_id        BIGINT NOT NULL REFERENCES users(id),
  body             TEXT NOT NULL,
  is_internal_note BOOLEAN NOT NULL DEFAULT false,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_messages_ticket ON ticket_messages(ticket_id);

CREATE TABLE ticket_embeddings (                 -- Week 3
  ticket_id  BIGINT PRIMARY KEY REFERENCES tickets(id) ON DELETE CASCADE,
  embedding  vector(768) NOT NULL
);
CREATE INDEX idx_ticket_embeddings_hnsw
  ON ticket_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE TABLE ai_suggestions (                    -- Week 3
  id          BIGSERIAL PRIMARY KEY,
  ticket_id   BIGINT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  type        TEXT NOT NULL CHECK (type IN ('classification','reply')),
  content     JSONB NOT NULL,
  model       TEXT NOT NULL,
  accepted    BOOLEAN,                            -- agent used it? = a real metric
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_suggestions_ticket ON ai_suggestions(ticket_id);

CREATE TABLE sla_policies (                       -- optional, Week 4/5
  id                BIGSERIAL PRIMARY KEY,
  org_id            BIGINT NOT NULL REFERENCES organizations(id),
  priority          TEXT NOT NULL CHECK (priority IN ('low','medium','high','urgent')),
  response_minutes  INT NOT NULL,
  resolution_minutes INT NOT NULL
);
```

**Alembic workflow:** define/modify the SQLAlchemy model → `alembic revision --autogenerate -m "add X"` → review the generated file → `alembic upgrade head`. The `vector` column needs the `pgvector` Python package's SQLAlchemy type; the `CREATE EXTENSION` line goes in the Week-3 migration manually.

---

## 3. Redis Keyspace Reference

| Key pattern | Purpose | TTL |
|---|---|---|
| `cache:tickets:{org_id}:{filter_hash}` | Cached ticket list | 30–60s + event-invalidated |
| `cache:analytics:{org_id}` | Cached analytics summary | 60s + event-invalidated |
| `session:refresh:{user_id}:{jti}` | Valid refresh tokens | = refresh expiry |
| `blocklist:{jti}` | Revoked tokens (logout) | = token expiry |
| `ratelimit:{user_id}` / `ratelimit:ai:{org_id}` | Token-bucket counters | window-based |
| `pubsub channel org:{org_id}` / `agent:{agent_id}` | WebSocket fan-out | n/a |
| `semcache:reply:{key}` | Reused AI reply drafts | 1h |
| Celery broker keys | Job queue | managed by Celery |

---

## 4. Environment Variables (`.env.example`)

```
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/support_desk
# Redis
REDIS_URL=redis://redis:6379/0
# Auth
JWT_SECRET=change-me
JWT_ALGO=HS256
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
# LLM (local in dev). From inside Docker, reach host Ollama via host.docker.internal
LLM_PROVIDER=local                # local | openai | anthropic
LLM_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=gemma4:e4b
EMBED_MODEL=nomic-embed-text
# Hosted (only if LLM_PROVIDER != local)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

---

## 5. Command Cheat-Sheet

```bash
# Whole stack
docker compose up -d --build
docker compose logs -f api worker

# Backend (inside the api container or a local venv)
alembic revision --autogenerate -m "message"
alembic upgrade head
celery -A worker.celery_app worker --loglevel=info

# Frontend
npm create vite@latest frontend -- --template react   # JS template (not react-ts)
cd frontend && npm install && npm run dev

# Tests
pytest                 # backend
npm run test           # Vitest (frontend)
npx playwright test    # e2e
```

---

# The Phases

Each phase: **Goal → Tasks → New deps → DB changes → Definition of Done → Commit.**

---

## Phase 0 — Bootstrap (½ day)

**Goal:** an empty but runnable skeleton.

**Tasks**
1. `git init`, create the top-level folders, add `.gitignore` (Python, Node, `.env`).
2. Write `docker-compose.yml` with `postgres` (image `pgvector/pgvector:pg16`), `redis` (`redis:7`), and placeholder `api` / `worker` / `frontend` services.
3. Add `.env.example`, copy to `.env`.
4. Confirm `docker compose up postgres redis` brings both up and you can connect.

**Definition of Done:** Postgres and Redis run locally via Compose; you can `psql`/GUI into the DB.
**Commit:** `chore: project bootstrap + infra compose`

---

## Phase 1 (Week 1) — Foundation & Core CRUD *(no AI yet)*

**Goal:** a working helpdesk you can click through — register, log in, create/list/view tickets, post messages.

**Tasks**
1. **Backend skeleton:** `main.py` (FastAPI app + `/health`), `config.py` (pydantic-settings), `db.py` (async engine + session), wire `get_db` in `deps.py`.
2. **Models + first migration:** `organizations`, `users`, `tickets`, `ticket_messages`. Run Alembic to create them.
3. **Auth:** `security.py` (Argon2 hashing, JWT access + refresh create/verify). Endpoints: `POST /auth/register` (creates org + admin on first signup, or joins existing), `POST /auth/login`, `POST /auth/refresh`. `get_current_user` + `require_role(...)` dependencies.
4. **Ticket + message endpoints:** `POST /tickets`, `GET /tickets` (scoped: customers see their own, agents/admins see the org's), `GET /tickets/{id}`, `PATCH /tickets/{id}` (status/assignment), `POST /tickets/{id}/messages`. Keep logic in `ticket_service.py`.
5. **Frontend skeleton:** scaffold Vite React (JS). Add `react-router-dom`, `axios`, `@tanstack/react-query`, Tailwind. Build `AuthContext`, `client.js` (attach JWT, refresh on 401), Login/Register pages, Tickets list + create form, TicketDetail with message thread.

**New deps:** backend — `fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pydantic-settings argon2-cffi pyjwt`. frontend — `react-router-dom axios @tanstack/react-query tailwindcss`.

**DB changes:** create the four core tables (migration #1).

**Definition of Done:** From a browser you can register, log in, create a ticket, see it in the list, open it, and post a reply. Refresh-token flow works. RBAC enforced (a customer can't see others' tickets).
**Commit:** `feat: auth, core ticket CRUD, base frontend`

---

## Phase 2 (Week 2) — Async + AI Classification

**Goal:** every new ticket gets auto-tagged with category, priority, and sentiment by the model — without blocking the API.

**Tasks**
1. **Celery setup:** `celery_app.py` (Redis broker/result backend); add the `worker` service to Compose; verify a trivial task runs.
2. **LLM client abstraction:** `ai/client.py` — an `LLMClient` with `complete()` and a `local` implementation calling Ollama (`{LLM_BASE_URL}/api/chat`) plus stubs for `openai`/`anthropic`, chosen by `LLM_PROVIDER`. Keep all prompt text in `ai/prompts.py`.
3. **Classification:** `ai/classify.py` — prompt the model for **strict JSON** `{category, priority, sentiment}`; parse and validate with a Pydantic schema; retry once on bad JSON, then fall back to safe defaults (`priority="medium"`, `category="general"`).
4. **Wire the flow:** `POST /tickets` enqueues `process_new_ticket(ticket_id)` and returns `201` immediately. The task loads the ticket, classifies, and updates the row.
5. **Frontend:** show the AI fields on the ticket detail; for now just refetch (TanStack Query `refetchInterval` or a manual refresh) — true real-time arrives in Week 4.

**New deps:** `celery[redis] redis httpx`.

**DB changes:** none (the `tickets` columns already exist). Optionally start writing classification results into `ai_suggestions` now if you add that table early.

**Definition of Done:** Create a ticket → within a couple of seconds its category/priority/sentiment populate. Killing the worker doesn't break ticket creation (graceful degradation).
**Commit:** `feat: celery worker + LLM classification pipeline`

---

## Phase 3 (Week 3) — Embeddings, Similar Tickets, Suggested Replies *(mini-RAG)*

**Goal:** the AI drafts a reply grounded in your own past resolved tickets — retrieval-augmented generation inside the product.

**Tasks**
1. **Enable pgvector:** migration adds `CREATE EXTENSION vector`, the `ticket_embeddings` table, and the HNSW index.
2. **Embeddings:** `ai/embeddings.py` — embed `subject + "\n" + body` via `nomic-embed`. In the worker, after classification, embed the ticket and upsert into `ticket_embeddings`.
3. **Similar tickets:** `GET /tickets/{id}/similar` — pgvector cosine search for the top-k **resolved** tickets in the same org (exclude the ticket itself).
4. **Suggested reply:** `ai/suggest.py` — build a prompt from the current ticket **plus the top similar resolved tickets and their accepted replies** as context; generate a draft; store it in `ai_suggestions` (`type='reply'`). Add `process_new_ticket` step to call it.
5. **Frontend AI panel:** `AiPanel.jsx` shows the classification, the similar tickets (clickable), and the suggested reply with **Accept / Edit / Send**. On accept, `POST /tickets/{id}/accept-suggestion/{id}` sets `accepted=true` and pre-fills the reply box.

**New deps:** `pgvector` (Python package for the SQLAlchemy `Vector` type). Embeddings via the same Ollama endpoint (`/api/embeddings`).

**DB changes:** `vector` extension, `ticket_embeddings`, `ai_suggestions` (migration #2).

**Definition of Done:** Open a ticket similar to a past resolved one → the AI panel shows relevant past tickets and a draft reply that clearly draws on them. Accepting a draft is recorded.
**Commit:** `feat: pgvector embeddings, similar-ticket retrieval, RAG reply suggestions`

---

## Phase 4 (Week 4) — Real-time + Caching + Dashboard

**Goal:** it feels like a real product — live updates, fast cached reads, a proper agent dashboard.

**Tasks**
1. **WebSocket:** `api/ws.py` — JWT-authenticated `/ws`; a connection manager subscribes each socket to its `org:{id}` (and `agent:{id}`) channel.
2. **Pub/sub bridge:** `core/events.py` — the worker publishes `ai.suggestion.ready`, `ticket.created`, `ticket.updated` to Redis; the API subscribes and pushes to the right sockets. (This is why pub/sub, not an in-process event bus: the producer is a *different process*.)
3. **Frontend real-time:** `useWebSocket.js` — on events, update the TanStack Query cache / show a toast ("New ticket", "Suggestion ready"). Live queue with no manual refresh.
4. **Caching:** `core/cache.py` — cache-aside for `GET /tickets` and analytics; **invalidate on the same events** that fire WebSocket updates (write → publish event → bust cache keys + notify clients). TTL as a backstop.
5. **Rate limiting:** `core/ratelimit.py` — token bucket per user, stricter per-org limit on AI-triggering actions.
6. **Semantic cache:** `ai/semantic_cache.py` — start simple (normalized-question key) and note the upgrade path to embedding-similarity matching.
7. **Dashboard:** `Dashboard.jsx` — live queue, priority + SLA-countdown badges, filters (status/priority/assignee).

**New deps:** none new (Redis already present).

**DB changes:** optional `sla_policies` if you compute `sla_due_at`.

**Definition of Done:** Two browser windows — create a ticket in one, watch it appear instantly in the agent dashboard in the other; the suggested reply pops in live when the worker finishes. Ticket lists are cached and correctly invalidated on changes. Hammering the AI endpoint trips the rate limiter.
**Commit:** `feat: websockets + redis pub/sub, caching with invalidation, dashboard`

---

## Phase 5 (Week 5) — Analytics, Tests, Docs, Deploy *(buffer / polish)*

**Goal:** portfolio-ready — measured, tested, documented, ideally live.

**Tasks**
1. **Analytics:** `GET /analytics/summary` (admin) — open vs resolved counts, average resolution time, and **AI suggestion acceptance rate** from `ai_suggestions.accepted`. Cached.
2. **Tests:** pytest for auth, ticket CRUD, RBAC, and the AI task with a **mocked** LLM client; Vitest for a couple of components; one Playwright happy-path (create ticket → triaged → agent accepts reply → resolved).
3. **Security pass:** confirm API keys are server-side only, input validated, AI JSON validated, CORS locked to the frontend origin, secrets not committed.
4. **Docs:** `README.md` with the architecture diagram (reuse the design doc), setup steps, and a `seed.py` that loads demo orgs/users/tickets so the app looks alive on first run.
5. **Deploy (optional):** containers to Railway/Render or a small VM; point the LLM client at a hosted model for the public demo.

**Definition of Done:** Green test suite, a README someone can follow to run it in one command, demo seed data, and (optionally) a live URL.
**Commit:** `feat: analytics, tests, docs, deploy`

**If you only have 3 weeks:** ship Phases 1–3, fold a light version of WebSockets + caching into the end of Week 3, and skip analytics + e2e. You still have a complete AI-integrated full-stack app.

---

## 6. Sequencing Notes & Gotchas

- **Build the non-AI helpdesk first (Week 1).** A solid CRUD core makes the AI work much easier to reason about. Resist adding AI early.
- **Mock the LLM in tests** so the suite is fast and deterministic — and so an interviewer sees you test around non-deterministic components.
- **Embedding dimension must match the model** (768 for nomic). If you swap embedding models later, you re-embed everything — note this in the README.
- **`host.docker.internal`** is how containers reach your host's Ollama on macOS; on Linux you may need `--add-host=host.docker.internal:host-gateway`.
- **Keep routers thin** — logic in `services/` and `ai/`. It makes testing and the eventual "why is this well-structured" interview answer easy.
- **The semantic cache is a stretch** — ship the simple normalized-key version first; only build embedding-similarity matching if you have time. Don't let it block Week 4.

---

*When you're ready, say "let's start Phase 0" (or any phase) and I'll generate the actual files for it — Compose, FastAPI skeleton, models, migrations — and we build it step by step.*
