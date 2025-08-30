from langchain_core.prompts import ChatPromptTemplate

from llms.cli import get_conversation_handle_fn
from llms.core import DEFAULT_CHAT_TEMPLATE, init_model

prompt = ChatPromptTemplate.from_template(DEFAULT_CHAT_TEMPLATE)
chain = prompt | init_model()


def llm_processing_fn(context: str, user_input: str) -> str:
    try:
        result = chain.invoke({"context": context, "question": user_input})
        print(f"Llama3.2: {result.strip()}")

        context += f"\nUser: {user_input}\nAI: {result.strip()}"

    except Exception as e:
        print(f"Llama3.2: Sorry, I encountered an error trying to respond. ({e})")
    return context


handle_conversation = get_conversation_handle_fn(llm_processing_fn)

if __name__ == "__main__":
    handle_conversation()
