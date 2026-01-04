from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field

class LogRecord(BaseModel):
    timestamp: Optional[datetime] = None
    product: Optional[str] = None
    service: Optional[str] = None
    environment: Optional[str] = None
    level: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[str] = None
    http_referer: Optional[str] = None
    user_agent: Optional[str] = None
    response_bytes: Optional[int] = None
    latency_ms: Optional[str] = None
    message: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Optional[dict] = None

class SearchQuery(BaseModel):
    start_date: Optional[date] = Field(None, description="Start date for filtering logs")
    end_date: Optional[date] = Field(None, description="End date for filtering logs")
    product: Optional[str] = Field(None, description="Filter by product name")
    service: Optional[str] = Field(None, description="Filter by service name")
    environment: Optional[str] = Field(None, description="Filter by environment")
    level: Optional[str] = Field(None, description="Filter by log level")
    trace_id: Optional[str] = Field(None, description="Filter by trace ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    span_id: Optional[str] = Field(None, description="Filter by span ID")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    method: Optional[str] = Field(None, description="Filter by HTTP method")
    status_code: Optional[str] = Field(None, description="Filter by HTTP status code")
    url_path: Optional[str] = Field(None, description="Filter by URL path")
    message: Optional[str] = Field(None, description="Filter by log message")
    latency_ms: Optional[int] = Field(None, description="Filter by latency in milliseconds")
    response_bytes: Optional[int] = Field(None, description="Filter by response size in bytes")
    page: int = Field(0, ge=0, description="Page number for pagination")
    page_size: int = Field(50, ge=1, le=100, description="Number of records per page for pagination")

class UniqueList(BaseModel):
    items: List[str]

class FilterOptions(BaseModel):
    dates: List[date]
    products: List[str]
    services: List[str]
    environments: List[str]
    levels: List[str]
    trace_ids: List[str]
    ip_addresses: List[str]
    methods: List[str]
    status_codes: List[int]
    url_paths: List[str]