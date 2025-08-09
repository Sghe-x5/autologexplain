from fastapi import APIRouter, Query

from schema import LogsResponse
from services.ch_service import fetch_logs_and_aggregates

router = APIRouter()

@router.get("/search", response_model=LogsResponse)
def search_logs(
    start_date: str,
    end_date: str,
    product: str | None = None,
    service: str | None = None,
    environment: str | None = None,
    level: str | None = None,
    trace_id: str | None = None,
    ip_address: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    url_path: str | None = None,
    page: int = 0,
    page_size: int = Query(50, ge=1, le=200),
):
    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "product": product,
        "service": service,
        "environment": environment,
        "level": level,
        "trace_id": trace_id,
        "ip_address": ip_address,
        "method": method,
        "status_code": status_code,
        "url_path": url_path,
        "page": page,
        "page_size": page_size,
    }
    return fetch_logs_and_aggregates(filters)

@router.get("/options")
def get_options():
    return {
        "products": [],
        "services": [],
        "environments": [],
        "levels": [],
        "methods": [],
        "status_codes": [],
    }
