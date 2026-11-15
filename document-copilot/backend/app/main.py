import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

log = structlog.get_logger()

app = FastAPI(title="Document Copilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
