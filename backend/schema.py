from typing import Optional, List
from pydantic import BaseModel, Field

class LogRecord(BaseModel):
    timestamp: str
    level: Optional[str] = None
    product: Optional[str] = None
    service: Optional[str] = None
    environment: Optional[str] = None
    message: str
    trace_id: Optional[str] = None
    ip_address: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    url_path: Optional[str] = None

class LogsResponse(BaseModel):
    samples: List[LogRecord] = Field(default_factory=list)
    aggregates: dict = Field(default_factory=dict)
    applied_sql: str = ""

class AnalysisStartRequest(BaseModel):
    chat_id: str
    filters: dict
    prompt: Optional[str] = None

class AnalysisStartResponse(BaseModel):
    request_id: str
    chat_id: str
    status: str = "accepted"
