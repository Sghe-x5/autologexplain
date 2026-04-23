from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.api.chats import router as chats_router
from backend.api.forecasting import router as forecasting_router
from backend.api.incidents import router as incidents_router
from backend.api.logs import router as logs_router
from backend.api.rca import router as rca_router
from backend.api.ws import router as ws_router
from backend.db.storage import init_store
from backend.services.incidents import ensure_ready as ensure_incidents_ready
from backend.services.signals import ensure_ready as ensure_signals_ready


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_store()
    ensure_signals_ready()
    ensure_incidents_ready()
    yield


app = FastAPI(title="AutoLog", lifespan=lifespan)
Instrumentator().instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chats_router, prefix="/chats", tags=["chats"])
app.include_router(logs_router, prefix="/logs", tags=["logs"])
app.include_router(incidents_router, prefix="/incidents", tags=["incidents"])
app.include_router(rca_router)
app.include_router(forecasting_router)
app.include_router(ws_router, tags=["ws"])
