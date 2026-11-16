from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat
from app.config import settings
from app.database.supabase import create_admin_client

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.supabase_admin = await create_admin_client()
    yield


app = FastAPI(title="Document Copilot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(chat.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Don't run this block in a notebook / VS Code interactive window. There
# `__name__` is also "__main__", but the kernel already has an event loop
# running, so uvicorn fails with "asyncio.run() cannot be called from a
# running event loop". `reload=True` also needs to spawn a separate process,
# which doesn't work from a notebook. Run only the code above it there (test
# with fastapi.testclient.TestClient), and start the real server from a
# terminal: `uv run uvicorn app.main:app --reload`.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", reload=True)
