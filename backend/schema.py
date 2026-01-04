from pydantic import BaseModel, Field


class LogRecord(BaseModel):
    timestamp: str
    level: str | None = None
    product: str | None = None
    service: str | None = None
    environment: str | None = None
    message: str
    trace_id: str | None = None
    ip_address: str | None = None
    method: str | None = None
    status_code: int | None = None
    url_path: str | None = None


class LogsResponse(BaseModel):
    samples: list[LogRecord] = Field(default_factory=list)  # UP006
    aggregates: dict = Field(default_factory=dict)
    applied_sql: str = ""


class AnalysisStartRequest(BaseModel):
    chat_id: str
    filters: dict
    prompt: str | None = None


class AnalysisStartResponse(BaseModel):
    request_id: str
    chat_id: str
    status: str = "accepted"
