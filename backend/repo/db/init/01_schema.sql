DROP TABLE IF EXISTS logs;

CREATE TABLE logs
(
  timestamp       DateTime64(6),       
  product         String,
  service         String,
  environment     String,
  level           String,
  trace_id        String,
  span_id         String,
  user_id         String,
  ip_address      String,
  method          String,
  status_code     Int32,
  url_path        String,
  http_referer    String,
  user_agent      String,
  response_bytes  Int64,
  latency_ms      Int64,
  message         String,
  stack_trace     String,
  metadata        String
)
ENGINE = MergeTree
ORDER BY (timestamp);