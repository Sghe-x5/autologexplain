from __future__ import annotations

import random
import time

_STUB_REPLIES = [
    "Похоже, всё норм. Если что — уточни интервал.",
    "Вижу пару аномалий, но нужно больше данных.",
    "Ошибка на стороне клиента не подтверждается.",
    "Есть всплеск WARN — возможно деградация внешнего сервиса.",
    "Метрик мало — проверь фильтры.",
]


def ask_llm(prompt: str, context: str | None = None) -> str:
    """Заглушка LLM: подождать 3 секунды и вернуть случайную фразу."""
    time.sleep(3)
    base = random.choice(_STUB_REPLIES)
    prompt = (prompt or "").strip()
    return f"{base}\n\nЗапрос: {prompt}" if prompt else base


def build_context(aggregates: dict | None = None, samples: list[dict] | None = None) -> str:
    """Заглушка контекста — для совместимости вызовов."""
    return "контекст отключён (заглушка)"
