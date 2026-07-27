import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from routers import auth, internal
from shared.response import success_response

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is created/migrated by `alembic upgrade head`, run in the
    # container entrypoint before this process starts (Fase 5,
    # BACKLOG.md E3) — not here anymore.
    yield


app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)


@app.get("/api/v1/auth/health")
def health():
    return success_response(
        data={"status": "ok", "service": "auth_service"},
        service="auth_service",
    )


app.include_router(auth.router)
app.include_router(internal.router)
