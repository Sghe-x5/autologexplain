from __future__ import annotations

from functools import lru_cache
from typing import Any

from analytics.core.agent import create_log_agent


@lru_cache(maxsize=256)
def _get_agent(chat_id: str):
    """
    Возвращает из кэша (или создаёт) агента для конкретного chat_id.
    У каждого чата — свой инстанс агента с собственной памятью.
    """
    return create_log_agent()


def ask_llm(prompt: str, chat_id: str) -> str:
    """
    Унифицированная точка входа для вызова ИИ.
    Контекст игнорируем (по вашему требованию), передаём только prompt.
    """
    agent = _get_agent(chat_id)
    result: dict[str, Any] = agent.invoke({"input": prompt})
    return str(result.get("output", ""))
