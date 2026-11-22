# Deploying to Vercel

The app is two Vercel projects built from the same GitHub repository and branch (`main`): the
FastAPI backend and the Vite frontend. No Dockerfile is needed: Vercel builds the backend from
`pyproject.toml` + `uv.lock` (entrypoint `app/main.py`, variable `app`) and the frontend with
`pnpm build`.

## 1. Supabase (dashboard)

- **Connect -> Transaction pooler**: copy the connection string (host `*.pooler.supabase.com`,
  port **6543**). Vercel connects over IPv4 only, and the direct host (`db.<ref>.supabase.co`) is
  IPv6, so the hosted backend must use the pooler. The backend turns off prepared statements,
  which the transaction pooler does not support (`app/database/engine.py`).
- **Authentication -> Sign In / Providers**: "Allow new users to sign up" on.
- **Authentication -> URL Configuration**: Site URL = the frontend URL (step 3).

Migrations are not run on Vercel. Run them from your machine with the direct URL in
`backend/.env`: `uv run alembic upgrade head` (Alembic refuses the transaction pooler).

## 2. Backend project

New Project -> import the repository -> **Root Directory** `document-copilot/backend`
(framework detected as FastAPI). Environment variables:

| Variable | Value | Why |
| -------- | ----- | --- |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | from Supabase -> API | Login checks and chat storage |
| `DATABASE_URL` | the transaction pooler string | Search over the filings (IPv4) |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_CHAT_MODEL`, `OPENAI_EMBEDDING_MODEL` | as in your local `.env` | The Azure model |
| `ALLOWED_ORIGINS` | the frontend URL (step 3), no trailing slash | Lets the browser call the API (CORS) |
| `FULL_ACCESS_EMAILS` | your email | Only these accounts get live answers; everyone else gets the samples |
| `LOG_FORMAT` | `json` | One searchable JSON object per log line ([logging.md](logging.md)) |

Deploy, then open `<backend URL>/health`: it should return `{"status":"ok"}`.

## 3. Frontend project

New Project -> same repository -> **Root Directory** `document-copilot/frontend` (framework
detected as Vite). Environment variables (read at build time, public values only):

| Variable | Value |
| -------- | ----- |
| `VITE_API_BASE_URL` | the backend URL from step 2 |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | from Supabase -> API (never the service-role key) |

`frontend/vercel.json` sends every path to `index.html`, so a link or refresh on
`/chat/<id>` works. `package.json` pins the pnpm version Vercel uses.

Then set the backend's `ALLOWED_ORIGINS` to this frontend URL and **redeploy the backend**.

## 4. Check it

- Sign up or sign in on the frontend URL.
- Another account: the three sample cards show; a sample opens with sources (tables in the panel);
  typing its own question shows the contact pop-up.
- Your account: a real question streams a cited answer.
- Refresh on a `/chat/<id>` page.
- Vercel -> backend -> Logs: JSON lines with `turn_started` / `turn_finished`.

## Known limits

- Preview deployments get a new URL each time, so CORS blocks them; only the production
  frontend URL can call the backend.
- Changing a `VITE_*` variable needs a frontend redeploy (it is built into the page).
