from typing import Callable

CHAT_START_DISPLAY = """
--- AI Chatbot (Powered by Llama3.2) ---
Ask me anything! Type 'exit' when you're done.
----------------------------------------
"""

CHAT_END_DISPLAY = """
----------------------------------------
Llama3.2: Goodbye! Thanks for chatting.
----------------------------------------
"""


def get_conversation_handle_fn(
    llm_processing_fn: Callable[[str, str], str],
) -> Callable[[], None]:
    def handle_fn():
        context = "The conversation has just begun."  # Start with a neutral context
        print(CHAT_START_DISPLAY)

        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                print(CHAT_END_DISPLAY)
                break

            print("Llama3.2: Thinking...")
            context = llm_processing_fn(context, user_input)
            print("----------------------------------------")

    return handle_fn
