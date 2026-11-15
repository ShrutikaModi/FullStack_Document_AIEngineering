# Document Copilot — Build Plan

**Problem:** Driftwood Capital analysts spend ~half their week on source-document intake (reading SEC filings). We're building an internal chatbot that answers plain-English questions over a curated 10-K/10-Q corpus, with **every claim cited to filing + page** and the underlying passage shown. It must never invent facts and must say so when the corpus lacks the answer.

**Success:** 5 pilot analysts each save ≥3 hrs/week.

**Out of scope:** stock picks / trading advice, external data (news, social), ungrounded analysis, multi-tenant, billing, mobile.

Stack (locked): FastAPI + PydanticAI · Vite/React/TS SPA · Supabase (Auth, Postgres, pgvector, FTS) · SQLAlchemy + Alembic · OpenAI · Railway.
Follow [CLAUDE.md](CLAUDE.md): minimal dependencies, single settings module per service, small focused modules.

Each phase ends with a **Done when** check. Don't start the next phase until it passes.

---

## Phase 0 — Foundations
- [ ] Create Supabase project; note URL, anon key, service-role key, direct (session) DB connection string
- [ ] Get an OpenAI API key
- [ ] Run `uv run data/download.py` to fetch the sample corpus (AAPL, AMZN, GOOGL, MSFT, NVDA 10-Ks, FY2021–2025)
- [ ] Skim [docs/guides/](docs/guides/) setup guides and [architecture.md](docs/architecture.md)

**Done when:** keys in hand and filings present in `data/downloads/`.

## Phase 1 — Scaffold backend and frontend
- [ ] Backend: FastAPI app skeleton in `backend/app/` with `main.py`, `config.py` (pydantic-settings, fail fast on missing vars), `/health` endpoint
- [ ] Backend: CORS from `ALLOWED_ORIGINS`; `structlog` logging
- [ ] Backend: `.env` from `.env.example`
- [ ] Frontend: Vite + React + TS app, React Router, Tailwind, shadcn/ui
- [ ] Frontend: `src/lib/env.ts` validating `VITE_*` vars
- [ ] Frontend: `.env` from `.env.example`

**Done when:** `GET /health` returns ok and the SPA loads in the browser.

## Phase 2 — Database schema (Alembic)
- [ ] SQLAlchemy models in `app/database/models.py`: `profiles`, `chat_threads`, `chat_messages`, `message_citations`, `source_documents`, `document_chunks`
- [ ] Alembic setup using the direct/session DB URL (not the pooler)
- [ ] Initial migration: `create extension vector`, `vector(1536)` column, generated `tsvector`, HNSW index (vector), GIN indexes (FTS + JSON metadata)
- [ ] RLS policies: users see only their own threads/messages/citations
- [ ] `uv run alembic upgrade head` against Supabase

**Done when:** all tables, indexes and extension visible in Supabase; migration re-runs cleanly on a fresh DB.

## Phase 3 — Auth
- [ ] Frontend: `src/lib/supabase.ts` client; login / sign-up / sign-out pages with email auth
- [ ] Frontend: protected routes (redirect to login when no session)
- [ ] Restrict sign-up to Driftwood email domain (backend check or Supabase auth hook)
- [ ] Backend: `app/auth/dependencies.py` — verify bearer token via Supabase Auth, expose `get_current_user`
- [ ] Backend: profile row created on first login
- [ ] Test: missing/invalid/expired token → 401

**Done when:** an analyst can log in and a protected backend endpoint returns their user; anonymous calls get 401.

## Phase 4 — API client and chat plumbing (stubbed assistant)
- [ ] Frontend: `src/lib/http.ts` (base URL, bearer injection, timeout, typed errors) and `src/lib/api.ts` (threads, messages)
- [ ] Backend: `app/database/chats.py` — create/list/read threads and messages, scoped to `user_id`
- [ ] Backend: thread endpoints (list, create, get messages); 403/404 for foreign/missing threads
- [ ] Backend: `POST /chat/stream` returning a **stubbed** AI-SDK-compatible stream
- [ ] Frontend: chat page using Vercel AI SDK `useChat` + `DefaultChatTransport` pointed at FastAPI
- [ ] Frontend: sidebar with the user's past conversations; new chat; load history
- [ ] Persist user + assistant messages after the run completes

**Done when:** a logged-in user chats with the stub, sees streaming text, refreshes, and finds the conversation in history.

## Phase 5 — Ingestion pipeline
- [ ] Parse SEC HTML filings → normalized Markdown, preserving page numbers and section headings (Item 1A, Item 7, etc.)
- [ ] Extract filing metadata: ticker, company, form type, fiscal year, filing date, accession number, source URL
- [ ] Store in `source_documents`
- [ ] Chunk by section/page with sensible size + overlap; record page, section, offsets, token count
- [ ] Batch-embed chunks with OpenAI (retry/backoff, idempotent re-runs)
- [ ] Write to `document_chunks`
- [ ] Ingestion CLI (e.g. `uv run python -m app.ingestion`), safe to re-run without duplicating rows
- [ ] Sanity checks: chunk counts per filing, no empty chunks, every chunk has a page

**Done when:** all sample filings are in Supabase with chunks and embeddings, and a spot-check of a few chunks matches the original filing pages.

## Phase 6 — Retrieval
- [ ] `retrieval/queries.py`: pgvector semantic search (bounded top-k)
- [ ] `retrieval/queries.py`: Postgres full-text search (bounded top-k)
- [ ] `retrieval/fusion.py`: Reciprocal Rank Fusion in Python
- [ ] `retrieval/retriever.py`: embed query → both searches → fuse → fetch chunks + doc metadata + neighbouring chunks
- [ ] Support metadata filters (company, fiscal year, form type) so multi-year/multi-company questions pull from each
- [ ] Unit tests for fusion and filters
- [ ] Manual check against brief questions: right filings/pages appear in top results

**Done when:** for several of the 10 brief questions, the expected passages show up in the top results.

## Phase 7 — PydanticAI document agent
- [ ] `assistant/outputs.py`: `GroundedAnswer`, `Citation`, `SourcePassage`
- [ ] `assistant/deps.py`: `DocumentAgentDeps` (user, thread, retriever, validator)
- [ ] `assistant/instructions.md`: answer only from retrieved passages; cite every claim; say "not enough evidence" when unsupported; no investment advice; refuse to infer beyond filings
- [ ] `assistant/agent.py`: agent with bounded tools `search_filings`, `read_chunk`, `read_surrounding_chunks` (no agent-written SQL)
- [ ] `chat/orchestrator.py`: one turn end-to-end (auth'd user → agent → result → persist)
- [ ] `chat/messages.py` + `chat/streaming.py`: AI SDK message ↔ internal types; stream text deltas and citation parts
- [ ] Replace the stub in `/chat/stream` with the real agent

**Done when:** asking a brief question streams a real answer with citation metadata.

## Phase 8 — Grounding enforcement
- [ ] `grounding/validator.py`: every citation maps to a passage retrieved in *this* request; every answer has ≥1 citation or an explicit insufficient-evidence statement
- [ ] On failure: controlled error response, never a polished unsupported answer
- [ ] Persist citations to `message_citations`
- [ ] Unit tests: valid citation, fabricated citation, missing citation, insufficient-evidence path
- [ ] Out-of-corpus questions ("What's Tesla's revenue?") return a clear "not in corpus"
- [ ] Advice requests ("Should I buy NVDA?") are declined

**Done when:** hallucination tests pass and unsupported answers are blocked.

## Phase 9 — Final chat UI
- [ ] `components/chat/*`: message list, streaming status, empty state with example questions
- [ ] Inline citation markers `[1]` → company, filing, fiscal year, page
- [ ] Source panel/popover showing the exact passage so the analyst can verify in one click
- [ ] Friendly error states (401, 502, network/CORS vs HTTP distinguished)
- [ ] Past-conversation list polish: titles, delete/rename (optional), loading states

**Done when:** an analyst can go question → cited answer → verified source passage without leaving the page.

## Phase 10 — Evaluation against the brief
- [ ] Turn the 10 brief questions into an eval set (question, expected companies/years, expected sections)
- [ ] Run each; record answer quality, citation correctness, latency, cost
- [ ] Check Q10 specifically: bot refuses to claim generative AI improved margins beyond filing evidence
- [ ] Tune chunk size, top-k, filters and prompt based on failures
- [ ] Add a few adversarial cases (missing year, fake company, leading questions)

**Done when:** all 10 questions give correct, cited, verifiable answers (or correct refusals).

## Phase 11 — Deploy (Railway)
- [ ] Backend service: Uvicorn start command, env vars, health check
- [ ] Frontend service: static Vite build
- [ ] Set production `ALLOWED_ORIGINS`, Supabase redirect URLs
- [ ] Run migrations against production Supabase (direct URL) and ingest the corpus
- [ ] Smoke test: login → ask → cited answer → history

**Done when:** the deployed app works end-to-end from a browser.

## Phase 12 — Pilot
- [ ] Create accounts for the 5 pilot analysts
- [ ] Short usage guide (what it can/can't answer)
- [ ] Log questions, latency, token usage, and refusals (no secrets)
- [ ] Collect feedback after one week; measure hours saved per analyst
- [ ] Decide: firm-wide rollout (target ≥3 hrs/analyst/week saved)

## Later (post-pilot, not now)
- [ ] Expand corpus to S&P 500 10-Ks/10-Qs, 2020–2025
- [ ] Local JWT verification if request volume grows
- [ ] Feedback buttons (thumbs up/down) on answers
