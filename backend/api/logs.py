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

@app.get("/logs/search", response_model=list[LogRecord])
def search_logs(
    start_date: str | None = Query(None, description="Start date for filtering logs"),
    end_date: str | None = Query(None, description="End date for filtering logs"),
    product: str | None = Query(None),
    service: str | None = Query(None),
    environment: str | None = Query(None),
    level: str | None = Query(None),
    trace_id: str | None = Query(None),
    ip_address: str | None = Query(None),
    method: str | None = Query(None),
    status_code: int | None = Query(None),
    url_path: str | None = Query(None),
    page: int = Query(0, ge=0),
    page_size: int = Query(50, ge=1, le=100)
):
    search = SearchQuery(
        start_date=start_date,
        end_date=end_date,
        product=product,
        service=service,
        environment=environment,
        level=level,
        trace_id=trace_id,
        ip_address=ip_address,
        method=method,
        status_code=status_code,
        url_path=url_path,
        page=page,
        page_size=page_size
    )
    sql, params = build_query(search)
    result = sql_query(sql, params)
    if not result:
        raise HTTPException(status_code=404, detail="Logs not found")
    return result

@app.get("/logs/services", response_model=UniqueList)
def get_log_services():
    sql = "SELECT DISTINCT service FROM logs ORDER BY service"
    result = sql_query(sql)
    if not result:
        raise HTTPException(status_code=404, detail="No services found")
    return UniqueList(items=[row["service"] for row in result])

@app.get("/logs/environments", response_model=UniqueList)
def get_unique_environments():
    sql = "SELECT DISTINCT environment FROM logs ORDER BY environment"
    result = sql_query(sql)
    if not result:
        raise HTTPException(status_code=404, detail="No environments found")
    return UniqueList(items=[row["environment"] for row in result])

@app.get("/logs/status_codes", response_model=UniqueList)
def get_unique_status_codes():
    sql = "SELECT DISTINCT status_code FROM logs ORDER BY status_code"
    result = sql_query(sql)
    if not result:
        raise HTTPException(status_code=404, detail="No status codes found")
    return UniqueList(items=[str(row["status_code"]) for row in result])


@app.get("/logs/options", response_model=FilterOptions)
def get_filter_options():
    sql_dates = "SELECT DISTINCT toDate(timestamp) AS date FROM logs ORDER BY date"
    rows = sql_query(sql_dates)
    dates = [ row["date"] for row in rows ]
    def fetch(field: str) -> list:
        sql = f"SELECT DISTINCT {field} FROM logs ORDER BY {field}"
        rs = sql_query(sql)
        return [ row[field] for row in rs ]

    try:
        return FilterOptions(
            dates=dates,
            products = fetch("product"),
            services = fetch("service"),
            environments = fetch("environment"),
            levels = fetch("level"),
            trace_ids = fetch("trace_id"),
            ip_addresses = fetch("ip_address"),
            methods = fetch("method"),
            status_codes = [str(x) for x in fetch("status_code")],
            url_paths = fetch("url_path"),
        )
    except KeyError:
        raise HTTPException(500, "Не удалось собрать фильтры из БД")