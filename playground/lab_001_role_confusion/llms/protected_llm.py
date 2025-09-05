from langchain_core.prompts import ChatPromptTemplate
import soteria_sdk

from llms.cli import get_conversation_handle_fn
from llms.core import DEFAULT_CHAT_TEMPLATE, init_model
from dotenv import load_dotenv
import os

load_dotenv()

soteria_api_key=os.getenv("SOTERIA_API_KEY")

soteria_sdk.configure(api_key=soteria_api_key, api_base="https://api.soteriainfra.com")

chat_prompt_template = ChatPromptTemplate.from_template(DEFAULT_CHAT_TEMPLATE)
chain = chat_prompt_template | init_model()


# This is the function that needs protection - it processes the user input
@soteria_sdk.guard_jailbreak
def protected_llm_call(prompt: Any):
    """
    Protected LLM call that blocks jailbreak attempts.
    """
    # Parse the prompt back into components for your chain
    lines = prompt.split("\n")

    context_start = False
    question_start = False
    context_lines = []
    question_lines = []

    for line in lines:
        if "Conversation History:" in line:
            context_start = True
            continue
        elif "Question:" in line:
            context_start = False
            question_start = True
            continue
        elif "Answer:" in line:
            question_start = False
            break

        if context_start:
            context_lines.append(line)
        elif question_start:
            question_lines.append(line)

    context_text = "\n".join(context_lines).strip()
    question_text = "\n".join(question_lines).strip()

    # Call your original chain
    result = chain.invoke({"context": context_text, "question": question_text})
    return result.strip()


def llm_processing_fn(context: str, user_input: str) -> str:
    try:
        full_prompt = f"""Answer the question below based on our conversation history
Conversation History:
{context}
Question:
{user_input}
Answer:"""
        # Add this print statement:
        print(f"--- Backend: Initial full_prompt sent to LLM ---\n'{full_prompt}'\n---------------------------------------------------------")

        # Use the protected function
        result = protected_llm_call(prompt=full_prompt)
        print(f"Llama3.2: {result}")
        context += f"\nUser: {user_input}\nAI: {result}"

    except soteria_sdk.SoteriaValidationError:
        print("Llama3.2: I can't process that request. Security filter activated.")
    except Exception as error:
        print(f"Llama3.2: Sorry, I encountered an error trying to respond. ({error})")
    return context


handle_conversation = get_conversation_handle_fn(llm_processing_fn)

if __name__ == "__main__":
    handle_conversation()
