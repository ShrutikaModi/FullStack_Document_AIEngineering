# Backend setup

This project uses a separate Python + FastAPI backend because the server is responsible for AI and document-processing work, not just basic web CRUD. Python gives us the strongest ecosystem for ingestion, chunking, embeddings, retrieval, evaluation, and LLM workflows. Keeping this logic behind a dedicated API also keeps the frontend focused on the user experience while the backend owns data access, orchestration, and grounding.

## Init (from empty `backend/`)

```bash
cd backend
# Reads pyproject.toml + uv.lock, creates backend/.venv, installs locked versions
uv sync
# Adds runtime dependencies to pyproject.toml and uv.lock
uv add fastapi uvicorn pydantic pydantic-settings httpx structlog openai supabase pydantic-ai sqlalchemy alembic "psycopg[binary]" pgvector
# Adds development-only tools (not installed in production)
uv add --dev pytest ruff
```

On a fresh clone, `uv sync` alone is enough: `pyproject.toml` already lists the runtime dependencies. Run the `uv add` lines only when starting from an empty `backend/` or when adding a new package.

### What each command does

- `cd backend` — `uv` looks for `pyproject.toml` in the current folder.
- `uv sync` — creates the virtual environment and installs the exact versions pinned in `uv.lock`. Adds nothing new.
- `uv add <packages>` — installs the packages and records them in `pyproject.toml` and `uv.lock`. Quote `"psycopg[binary]"` so zsh doesn't treat the brackets as a glob.
- `uv add --dev pytest ruff` — installs development-only tools in a separate dependency group.

### Runtime dependencies

| Package | Use |
| ------- | --- |
| `fastapi` | Web framework for the API (`/health`, `/chat/stream`, thread endpoints) |
| `uvicorn` | ASGI server that runs the FastAPI app |
| `pydantic` | Typed models for requests, responses, and `GroundedAnswer` |
| `pydantic-settings` | Loads and validates `.env` in `app/config.py`; fails fast on missing values |
| `httpx` | HTTP client for outbound calls |
| `structlog` | Structured logging |
| `openai` | OpenAI SDK for embeddings and LLM calls |
| `supabase` | Supabase client for token verification and server-side data access |
| `pydantic-ai` | Typed agent framework for the document agent and its tools |
| `sqlalchemy` | Table models that Alembic reads to generate migrations |
| `alembic` | Database migrations (`uv run alembic upgrade head`) |
| `psycopg[binary]` | Postgres driver used by SQLAlchemy and Alembic; `[binary]` ships a prebuilt version, so no C compiler is needed |
| `pgvector` | Python support for the `vector` column type (embeddings) |

### Development dependencies

| Package | Use |
| ------- | --- |
| `pytest` | Runs backend tests (retrieval fusion, grounding validation, auth) |
| `ruff` | Linter and formatter |

Run them with `uv run pytest` and `uv run ruff check .`.

## Database migrations

Alembic owns database schema changes for this project. SQLAlchemy models describe the app tables, and Alembic migrations apply those changes to Supabase Postgres.

Initialize Alembic once from `backend/`:

```bash
uv run alembic init alembic
```

Configure `alembic/env.py` to import the app's SQLAlchemy metadata and read the direct database URL from `app.config.settings`. Use the direct/session Supabase database connection, not the transaction pooler URL, for migrations.

Create a migration after changing SQLAlchemy models:

```bash
uv run alembic revision --autogenerate -m "add document tables"
```

Always review the generated migration. Add explicit operations for Supabase/Postgres features that autogenerate cannot reliably infer:

- `create extension if not exists vector`
- `vector(1536)` columns
- generated `tsvector` columns
- HNSW and GIN indexes
- RLS enablement and policies

Apply migrations:

```bash
uv run alembic upgrade head
```

## Run

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Imports (`from app...`)

`backend/app` is installed as an editable package by `uv sync`, so `from app...` imports work from uvicorn, direct Python execution, tests, and Jupyter kernels that use the backend venv.

The `[build-system]` and `[tool.hatch.build.targets.wheel]` sections in `backend/pyproject.toml` tell uv how to install the local `app/` package. Without that package install, imports depend on the current working directory or a manually configured `PYTHONPATH`, which is fragile in notebooks and IDE run buttons.

Preferred API server command:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Direct file execution also works:

```bash
cd backend
uv run python app/main.py
```

For Jupyter, install and select the backend kernel:

```bash
cd backend
uv run python -m ipykernel install --user --name document-copilot-backend --display-name "Document Copilot Backend"
```

Then notebooks can import backend modules:

```python
from app.config import settings
```

## Sample SEC data

From the repo root (stdlib-only script, no backend env needed):

```bash
uv run data/download.py
```
