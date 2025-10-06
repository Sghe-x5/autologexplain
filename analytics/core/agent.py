from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import BasePromptTemplate, PromptTemplate
from langchain.tools.render import render_text_description
from langchain_openai import ChatOpenAI
from langchain_community.chat_models.yandex import ChatYandexGPT
from pydantic import SecretStr

from analytics.core.tools.profiler_tool import data_profiler
from analytics.core.tools.specialized_tools import python_code_interpreter, trace_retriever
from analytics.core.tools.sql_query_tool import safe_sql_query_executor
from analytics.utils.config import (
    AI_STUDIO_BASE_URL,
    LLM_MODEL_NAME,
    SYSTEM_PROMT,
    YC_API_KEY,
    YC_FOLDER_ID,
    token_manager 
)


def _resolve_model_uri(model_name: str, folder_id: str) -> str:
    if "://" in model_name:
        return model_name
    return f"gpt://{folder_id}/{model_name}/latest"


def create_log_agent() -> AgentExecutor:
    tools = [
        safe_sql_query_executor,
        data_profiler,
        trace_retriever,
        python_code_interpreter,
    ]
    # Приоритет: API-ключ (простой, без JWT) > IAM-токен (через service account).
    # API-ключ удобнее для dev/demo; IAM-токен нужен когда у сервисного аккаунта
    # особые права (например, логирование в YC).
    llm = None
    if YC_API_KEY:
        llm = ChatOpenAI(
            api_key=YC_API_KEY,
            base_url=AI_STUDIO_BASE_URL,
            model=_resolve_model_uri(LLM_MODEL_NAME, YC_FOLDER_ID or ""),
            default_headers={"OpenAI-Project": YC_FOLDER_ID or ""},
            temperature=0.0,
            max_tokens=4096,
            max_retries=1,
            timeout=30,
        )
    else:
        yc_iam_token = None
        if token_manager is not None:
            try:
                yc_iam_token = token_manager.get_token()
            except Exception:
                yc_iam_token = None
        if yc_iam_token:
            llm = ChatYandexGPT(
                iam_token=SecretStr(yc_iam_token),
                folder_id=YC_FOLDER_ID or "",
                model_name=LLM_MODEL_NAME,
                temperature=0.0,
                max_tokens=4096,
                max_retries=1,
                sleep_interval=1.0,
            )
    if llm is None:
        raise ValueError(
            "Не найдены YC_API_KEY или данные сервисного аккаунта для получения YC_IAM_TOKEN"
        )

    system_prompt = SYSTEM_PROMT

    prompt: BasePromptTemplate = PromptTemplate.from_template(system_prompt)

    prompt = prompt.partial(
        tools=render_text_description(tools),
        tool_names=", ".join([t.name for t in tools]),
    )

    agent = create_react_agent(llm, tools, prompt)

    memory = ConversationBufferWindowMemory(k=30, memory_key="chat_history", return_messages=False)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        memory=memory,
        handle_parsing_errors=True,
        max_iterations=30,
    )

    return agent_executor
