from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from backend.api.chats import router as chats_router
from backend.api.logs import router as logs_router
from backend.api.ws import router as ws_router
from backend.db.storage import init_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_store()
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
app.include_router(ws_router, tags=["ws"])
