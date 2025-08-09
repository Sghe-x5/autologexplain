ATTACH TABLE _ UUID 'ba9ff898-a24f-4cbd-9d4a-1114c3f97329'
(
    `timestamp` DateTime64(6),
    `product` String,
    `service` String,
    `environment` String,
    `level` String,
    `trace_id` String,
    `span_id` String,
    `user_id` String,
    `ip_address` String,
    `method` String,
    `status_code` Int32,
    `url_path` String,
    `http_referer` String,
    `user_agent` String,
    `response_bytes` Int64,
    `latency_ms` Int64,
    `message` String,
    `stack_trace` String,
    `metadata` String
)
ENGINE = MergeTree
ORDER BY timestamp
SETTINGS index_granularity = 8192
