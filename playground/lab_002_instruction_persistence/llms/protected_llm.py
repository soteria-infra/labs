import os
import uuid
from typing import Any
import soteria_sdk
from langchain_community.chat_message_histories.file import FileChatMessageHistory
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import ConfigurableFieldSpec
from dotenv import load_dotenv

load_dotenv()

# --- Soteria SDK Configuration ---
soteria_api_key = os.getenv("SOTERIA_API_KEY")
if not soteria_api_key:
    print("WARNING: SOTERIA_API_KEY environment variable not set. Soteria protection will not be active.")
else:
    soteria_sdk.configure(api_key=soteria_api_key, api_base="https://api.soteriainfra.com")


HISTORY_DIR_PROTECTED = "json_chat_histories_auto_id_protected"
os.makedirs(HISTORY_DIR_PROTECTED, exist_ok=True)

def get_session_history_protected(session_id: str, user_id: str):
    """
    Retrieves or creates a file-based chat message history for a given session and user in protected mode.
    """
    file_name = f"history_{user_id}_{session_id}.json"
    file_path = os.path.join(HISTORY_DIR_PROTECTED, file_name)
    return FileChatMessageHistory(file_path=file_path)

try:
    model_protected = OllamaLLM(model="llama3.2")
    parser_protected = StrOutputParser()
except Exception as e:
    print(f"Error initializing OllamaLLM or StrOutputParser for protected mode: {e}")
    model_protected = None
    parser_protected = None


chat_prompt_template_protected = ChatPromptTemplate.from_messages([
    SystemMessage(content="You are a helpful assistant. Answer all questions to the best of your ability."),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{question}")
])

if model_protected and parser_protected:
    chain_base_protected = chat_prompt_template_protected | model_protected | parser_protected
else:
    chain_base_protected = None

runnable_with_history_protected = None
if chain_base_protected:
    runnable_with_history_protected = RunnableWithMessageHistory(
        runnable=chain_base_protected,
        input_messages_key="question",
        get_session_history=get_session_history_protected,
        history_factory_config=[
            ConfigurableFieldSpec(
                id="session_id",
                annotation=str,
                name="Session ID",
                description="Unique identifier for the conversation session.",
                default="",
                is_shared=True
            ),
            ConfigurableFieldSpec(
                id="user_id",
                annotation=str,
                name="User ID",
                description="Unique identifier for the user.",
                default="",
                is_shared=True
            ),
        ],
        history_messages_key="history"
    )

@soteria_sdk.guard_prompt_injection
def protected_chat_handler(prompt: str, session_id: str, user_id: str):
    """
    Protected LLM call that blocks prompt injection attempts.
    The 'prompt' argument will be inspected by the Soteria SDK.
    """
    if runnable_with_history_protected is None:
        return "LLM service for protected mode is unavailable due to an initialization error."

    return runnable_with_history_protected.invoke(
        {"question": prompt},
        config={"configurable": {"session_id": session_id, "user_id": user_id}}
    )

template_protected = chat_prompt_template_protected