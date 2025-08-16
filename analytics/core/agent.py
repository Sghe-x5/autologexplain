from langchain.agents import AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import BasePromptTemplate, PromptTemplate
from langchain.tools.render import render_text_description
from langchain_community.chat_models.yandex import ChatYandexGPT

from analytics.core.tools.profiler_tool import data_profiler
from analytics.core.tools.specialized_tools import python_code_interpreter, trace_retriever
from analytics.core.tools.sql_query_tool import safe_sql_query_executor
from analytics.utils.config import (
    LLM_MODEL_NAME,
    SYSTEM_PROMT,
    YC_API_KEY,
    YC_FOLDER_ID,
    YC_IAM_TOKEN,
)


def create_log_agent() -> AgentExecutor:
    tools = [
        safe_sql_query_executor,
        data_profiler,
        trace_retriever,
        python_code_interpreter,
    ]

    if YC_IAM_TOKEN:
        llm = ChatYandexGPT(
            iam_token=YC_IAM_TOKEN,
            folder_id=YC_FOLDER_ID,
            model_name=LLM_MODEL_NAME,
            temperature=0.0,
            max_tokens=4096,
        )
    elif YC_API_KEY:
        llm = ChatYandexGPT(
            api_key=YC_API_KEY,
            folder_id=YC_FOLDER_ID,
            model_name=LLM_MODEL_NAME,
            temperature=0.0,
            max_tokens=4096,
        )
    else:
        raise ValueError("Не найдены ни YC_IAM_TOKEN, ни YC_API_KEY в файле .env")

    system_prompt = SYSTEM_PROMT

    prompt: BasePromptTemplate = PromptTemplate.from_template(system_prompt)

    prompt = prompt.partial(
        tools=render_text_description(tools),
        tool_names=", ".join([t.name for t in tools]),
    )

    agent = create_react_agent(llm, tools, prompt)

    memory = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=False)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        memory=memory,
        handle_parsing_errors=True,
        max_iterations=15,
    )

    return agent_executor
