import random


def ask_llm(prompt: str, context: str) -> str:
    # Мок ответа LLM
    variants = [
        "Похоже, всплеск ошибок связан с недоступностью внешнего API.",
        "Основная нагрузка приходится на сервис логина; время ответа выросло.",
        "Аномалий за указанный период не найдено.",
    ]
    return random.choice(variants)

def build_context(aggregates: dict, samples: list[dict]) -> str:
    total = aggregates.get("total", 0)
    errors = aggregates.get("errors", 0)
    return f"Всего записей: {total}, ошибок: {errors}. Примеров: {len(samples)}."
