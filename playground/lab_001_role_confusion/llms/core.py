from langchain_ollama import OllamaLLM

DEFAULT_CHAT_TEMPLATE = """
Answer the question below based on our conversation history

Conversation History: 
{context}

Question: 
{question}

Answer:
"""


def init_model() -> OllamaLLM:
    try:
        return OllamaLLM(model="llama3.2")
    except Exception as error:
        print(f"Error Initializing the LLM.\nDetails: {error}")
        exit()
