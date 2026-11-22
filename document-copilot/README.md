# Document Copilot

An internal AI chatbot that lets analysts query a corpus of documents in plain English and get sourced, citable answers.

## The client

**Driftwood Capital** — fictional independent investment research firm. Their analysts spend half their week reading 10-Ks and 10-Qs before they can produce any original analysis. Document Copilot eats that intake work so they can skip straight to insight.

Full brief: [docs/client-brief.md](docs/client-brief.md)

## Stack

| Layer              | Choice                                               |
| ------------------ | ---------------------------------------------------- |
| Backend            | Python + FastAPI                                     |
| Frontend           | Vite + React SPA + TypeScript                        |
| Database           | Supabase Postgres (users, chats, documents, chunks)  |
| Migrations         | SQLAlchemy models + Alembic                          |
| Retrieval          | Supabase `pgvector` + Postgres full-text search      |
| Auth               | Supabase Auth (email only)                           |
| Hosting            | Railway                                              |
| LLM + embeddings   | OpenAI API or Azure OpenAI (same SDK)                |
| Agent              | PydanticAI (cited, validated answers)                |

## Repo layout

```text
document-copilot/
├── AGENTS.md           # agent instructions (read first)
├── README.md           # this file
├── todo.md             # phase-by-phase checklist
├── data/               # local corpus + download script (payloads gitignored)
├── docs/               # client brief, architecture, how retrieval + grounding work, setup guides
├── backend/            # FastAPI service (app/), ingestion scripts (ingest/), evals (evals/)
└── frontend/           # React SPA (Vite)
```

## Prerequisites

Install these before setting up `backend/` or `frontend/`:

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.12+ | Backend runtime | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + `data/download.py` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need accounts/keys for external services once the app is wired up. Start with [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) (account + project), then create an [OpenAI API key](https://platform.openai.com/api-keys) when the LLM layer is wired up.

## Running locally

You need a Supabase project and an OpenAI key (or an Azure OpenAI deployment). Account and
project setup is in [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md).

**1. Backend** (from `backend/`)

```bash
uv sync
cp .env.example .env        # then fill in the Supabase, database and OpenAI values
uv run alembic upgrade head # create the tables (uses the DIRECT database connection)
uv run uvicorn app.main:app --reload
```

The API runs at http://localhost:8000 (`GET /health` should return 200). For Azure OpenAI set
`OPENAI_BASE_URL` and use your deployment names for `OPENAI_CHAT_MODEL` and
`OPENAI_EMBEDDING_MODEL`; every variable is explained in `backend/.env.example`.

**2. Frontend** (from `frontend/`)

```bash
pnpm install
cp .env.example .env        # backend URL + Supabase URL and anon key (public values only)
pnpm dev
```

Open http://localhost:5173, sign up with an email, and ask a question about the filings. The
corpus must be loaded first (next section) or every answer will say there is not enough evidence.

**Who gets the real assistant:** only confirmed emails listed in `FULL_ACCESS_EMAILS` (in
`backend/.env`, and in the hosting environment). Every other account is in demo mode: they can open
three recorded sample questions (answers, steps and sources, no model call) and get a "reach out"
message for anything they type. The decision is made on the server from the verified login. Leave
the variable empty and everyone is in demo mode. The samples live in `backend/app/demo/recorded.py`;
re-record them with `uv run python -m evals.record_demo` (real model calls; it retries until an answer
passes the checks in `app/demo/checks.py`) after re-ingesting the filings, read the printed answers,
then run `uv run pytest tests/demo`.

**Logs:** each question writes a few log lines (`turn_started`, `tool_call`, `model_response`,
`turn_finished`) that share a `request_id`, `thread_id` and `user_id`. Locally they are coloured
and readable; on Railway set `LOG_FORMAT=json` for one JSON object per line. The question text is
never logged, only its length. What each line means and how to trace a failed turn:
[docs/logging.md](docs/logging.md).

**macOS note:** if `from app...` fails with `No module named 'app'` outside `backend/`
(for example in an editor's Interactive window), macOS has flagged the editable-install file
as hidden. Run `chflags -R nohidden backend/.venv` once.

## Loading the filings

The corpus is the latest five 10-Ks of AAPL, MSFT, NVDA, AMZN, GOOGL, JPM, TSLA and META
(40 filings, about 10,000 chunks). Every step can be re-run safely.

```bash
# from the repo root: edit USER_AGENT in data/download.py first (SEC requires a contact)
uv run data/download.py

# from backend/
uv run python -m ingest.to_markdown                      # HTML -> Markdown (Docling, slow)
uv run python ingest/build_markdown_manifest.py          # list of converted filings
uv run python -m ingest.load_filings                     # chunk + store (skips existing filings)
uv run python -m ingest.embed_chunks                     # embeddings for chunks that lack one
```

Adding a company or year later: add it to `data/download.py`, then run the same steps; filings
already in the database are skipped. How the chunks are searched is in
[docs/retrieval-and-grounding.md](docs/retrieval-and-grounding.md).

## Checking that it works

Run from `backend/` (the first two are free and need no network):

| What it checks | Command |
| -------------- | ------- |
| Code style | `uv run ruff check .` |
| Rules, tools, citation validator, chat flow, history (offline) | `uv run pytest` |
| Real searches over the ingested filings | `uv run pytest -m integration tests/retrieval` |
| One full turn with the real model and database, saved and reloaded | `uv run pytest -m integration tests/chat/test_turn_live.py` |
| Search quality (keyword vs vector vs hybrid) | `uv run python -m evals.retrieval_eval` |
| Answer behaviour on 21 cases, repeated, with tokens and time (about $1) | `uv run python -m evals.grounding_eval` |
| Try any conversation and see the searches and sources | `uv run python -m evals.try_conversation "Q1" "Q2"` |

The integration tests and evals call the real model and database. The frontend has no test
suite by project rule: check it with `pnpm tsc --noEmit -p tsconfig.app.json`, `pnpm lint` and
`pnpm build`, then in the browser.

## Sample SEC data

`data/download.py` fetches the 10-K filings from SEC EDGAR (see "Loading the filings" for the
full steps). Edit the parameters at the top, especially `USER_AGENT`, then run
`uv run data/download.py` from the repo root. By default it downloads the latest 5 10-Ks for 8
companies into year folders under `data/downloads/` and writes a `manifest.json`. Downloaded
files are gitignored; the `data/` folder itself stays in git for the script and notes.
