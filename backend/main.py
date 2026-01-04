from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.analysis import router as analysis_router
from api.logs import router as logs_router
from api.ws import router as ws_router
from backend.db.storage import init_store

app = FastAPI(title="AutoLog (no-Postgres)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ограничь в prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs_router, prefix="/logs", tags=["logs"])
app.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
app.include_router(ws_router, tags=["ws"])

@app.on_event("startup")
def on_startup():
    # сейчас хранение — в Redis, инициализация — no-op
    init_store()
