from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.logs import router as logs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="AutoLog", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs_router, prefix="/logs", tags=["logs"])
