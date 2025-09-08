import os
import uuid
from langchain_community.chat_message_histories.file import FileChatMessageHistory
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import ConfigurableFieldSpec

# Define a directory to store your JSON history files for vulnerable mode
HISTORY_DIR_VULNERABLE = "json_chat_histories_auto_id_vulnerable"
os.makedirs(HISTORY_DIR_VULNERABLE, exist_ok=True)

def get_session_history_vulnerable(session_id: str, user_id: str):
    """
    Retrieves or creates a file-based chat message history for a given session and user in vulnerable mode.
    """
    file_name = f"history_{user_id}_{session_id}.json"
    file_path = os.path.join(HISTORY_DIR_VULNERABLE, file_name)
    return FileChatMessageHistory(file_path=file_path)


try:
    model_vulnerable = OllamaLLM(model="llama3.2")
    parser_vulnerable = StrOutputParser()
except Exception as e:
    print(f"Error initializing OllamaLLM or StrOutputParser for vulnerable mode: {e}")
    model_vulnerable = None
    parser_vulnerable = None


chat_prompt_template_vulnerable = ChatPromptTemplate.from_messages([
    SystemMessage(content="You are a helpful assistant. Answer all questions to the best of your ability."),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{question}")
])

if model_vulnerable and parser_vulnerable:
    chain_base_vulnerable = chat_prompt_template_vulnerable | model_vulnerable | parser_vulnerable
else:
    chain_base_vulnerable = None


runnable_with_history_vulnerable = None
if chain_base_vulnerable:
    runnable_with_history_vulnerable = RunnableWithMessageHistory(
        runnable=chain_base_vulnerable,
        input_messages_key="question",
        get_session_history=get_session_history_vulnerable,
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