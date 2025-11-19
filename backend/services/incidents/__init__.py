from loguru import logger
from typing import Any, Mapping

def log_cycle_result(worker_name: str, result: Mapping[str, Any]) -> None:
    logger.info("{} finished: {}", worker_name, json.dumps(dict(result), ensure_ascii=False))
