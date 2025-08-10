# core/agent.py
from langchain_openai import ChatOpenAI 
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from utils.config import OPENROUTER_API_KEY, LLM_MODEL_NAME

# <<< ИЗМЕНЕНИЕ: Импортируем ВСЕ необходимые инструменты
from core.tools.sql_query_tool import safe_sql_query_executor
from core.tools.specialized_tools import trace_retriever, python_code_interpreter
from core.tools.profiler_tool import data_profiler

def create_log_agent():
    # <<< ИЗМЕНЕНИЕ: Добавляем новый инструмент в арсенал
    tools = [
        safe_sql_query_executor,
        data_profiler, # Новый "орган чувств" агента
        trace_retriever,
        python_code_interpreter,
    ]
    
    llm = ChatOpenAI(
        model=LLM_MODEL_NAME,
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        temperature=0.0,
        max_tokens=4096,
        default_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "LogSentry AI Agent",
        }
    )
    
    # <<< ГЛАВНОЕ ИЗМЕНЕНИЕ: Новый, более умный системный промпт
    system_prompt = """
    Ты — LogSentry, элитный SQL-аналитик-детектив. Твоя задача — не просто писать SQL, а проводить расследования, чтобы найти точный ответ на вопрос пользователя. Ты работаешь с таблицей `logs` в ClickHouse.

    **Ключевые колонки:** `timestamp`, `product`, `service`, `environment`, `level`, `status_code`, `latency_ms`, `message`, `trace_id`.

    **ТВОЙ РАБОЧИЙ ПРОЦЕСС (МЫСЛИ КАК ДЕТЕКТИВ):**

    1.  **ОПТИМИСТИЧНАЯ ПОПЫТКА:** Сначала напиши SQL-запрос, чтобы ответить на вопрос пользователя, и выполни его с помощью `safe-sql-query-executor`. ВСЕГДА используй `LIMIT`.

    2.  **АНАЛИЗ УЛИК (РЕЗУЛЬТАТА):**
        *   **Если получил данные:** Отлично! Проанализируй их и дай ответ пользователю.
        *   **Если получил ошибку SQL:** Прочти текст ошибки, исправь синтаксис своего SQL и попробуй снова.
        *   **Если получил ПУСТОЙ РЕЗУЛЬТАТ:** ЭТО НЕ КОНЕЦ, ЭТО УЛИКА! Не сдавайся. Твоя первая гипотеза должна быть: "Я использовал неверное значение в условии WHERE".

    3.  **СБОР ДОПОЛНИТЕЛЬНЫХ ДАННЫХ:**
        *   Чтобы проверить свою гипотезу, используй инструмент `data-profiler`. Например, если ты написал `WHERE level = 'error'` и получил пустой результат, вызови `data_profiler` с `column_name='level'`.
        *   Инструмент вернет тебе РЕАЛЬНЫЕ значения из базы данных (например, `['INFO', 'ERROR', 'WARN']`).

    4.  **КОРРЕКЦИЯ И ПОВТОРНАЯ ПОПЫТКА:**
        *   Сравнив свой запрос с реальными данными, ты увидишь свою ошибку (например, что нужно было писать 'ERROR', а не 'error').
        *   Напиши ИСПРАВЛЕННЫЙ SQL-запрос и выполни его снова с помощью `safe-sql-query-executor`.

    5.  **ФИНАЛЬНЫЙ ВЫВОД:**
        *   Только если и твоя вторая, исправленная попытка вернула пустой результат, ты можешь с уверенностью сказать пользователю, что таких данных нет.

    Твоя ценность — в твоей настойчивости и способности исправлять собственные ошибки на основе данных. Действуй.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    memory = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, memory=memory,
        handle_parsing_errors=True,
        max_iterations=15 
    )
    
    return agent_executor