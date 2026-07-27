import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from consumer import start_consuming
from shared.response import success_response

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is migrated by `alembic upgrade head` in the container
    # entrypoint, before this process starts (Fase 5, BACKLOG.md E3).
    thread = threading.Thread(target=start_consuming, daemon=True)
    thread.start()
    yield


app = FastAPI(title="Analysis Service", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)


@app.get("/api/v1/analyses/health")
def health():
    return success_response(
        data={"status": "ok", "service": "analysis_service"},
        service="analysis_service",
    )
