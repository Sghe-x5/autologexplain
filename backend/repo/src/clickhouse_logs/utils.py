from __future__ import annotations
from typing import Dict, List, Tuple
from .schema import SearchQuery

ALLOWED_FILTERS = {
    "start_date": "timestamp >= {start_date}",
    "end_date": "timestamp <= {end_date}",
    "product": "product = {product}",
    "service": "service = {service}",
    "environment": "environment = {environment}",
    "level": "level = {level}",     
    "trace_id": "trace_id = {trace_id}",
    "user_id": "user_id = {user_id}",
    "span_id": "span_id = {span_id}",
    "ip_address": "ip_address = {ip_address}",
    "method": "method = {method}",
    "status_code": "status_code = {status_code}",
    "url_path": "url_path ILIKE {url_path}",
    "message": "message ILIKE {message}",
    "latency_ms": "latency_ms = {latency_ms}",
    "response_bytes": "response_bytes = {response_bytes}",
}


def build_query(query: SearchQuery) -> Tuple[str, Dict[str, str]]:
    filters: List[str] = []
    params: Dict[str, str] = {}

    for field, condition in ALLOWED_FILTERS.items():
        value = getattr(query, field)
        if value is not None:
            filters.append(condition.format(**{field: f"'{value}'" if isinstance(value, str) else value}))
            params[field] = value

    where_clause = " AND ".join(filters) if filters else "1=1"
    sql = f"""
    SELECT * FROM logs WHERE {where_clause} ORDER BY timestamp DESC LIMIT {query.page_size} OFFSET {query.page * query.page_size}
    """
    return sql, params
