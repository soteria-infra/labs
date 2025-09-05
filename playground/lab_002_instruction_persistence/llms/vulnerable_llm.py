import os
import uuid # Import uuid for generating unique IDs
from langchain_community.chat_message_histories.file import FileChatMessageHistory
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import ConfigurableFieldSpec

# Define a directory to store your JSON history files
HISTORY_DIR = "json_chat_histories_auto_id"
# Create the directory if it doesn't exist
os.makedirs(HISTORY_DIR, exist_ok=True)

def get_session_history(session_id: str, user_id: str):
    """
    Retrieves or creates a file-based chat message history for a given session and user.
    """
    file_name = f"history_{user_id}_{session_id}.json"
    file_path = os.path.join(HISTORY_DIR, file_name)
    print(f"Loading/creating JSON history file: {file_path}")
    return FileChatMessageHistory(file_path=file_path)

# Initialize the LLM
try:
    model = OllamaLLM(model="llama3.2")
    parser = StrOutputParser()
except Exception as e:
    print(f"Error initializing OllamaLLM or StrOutputParser: {e}")
    exit()

# Define the chat prompt template
chat_prompt_template = ChatPromptTemplate.from_messages([
    SystemMessage(content="You are a helpful assistant. Answer all questions to the best of your ability."),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{question}")
])

# Create the chain: prompt -> model -> parser
chain = chat_prompt_template | model | parser

# Wrap the chain with history management
runnable_with_history = RunnableWithMessageHistory(
    runnable=chain,
    input_messages_key="question",
    get_session_history=get_session_history,
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

# --- Modified Interaction Loop with Auto-Generated IDs ---
if __name__ == "__main__":
    print("\n--- AI Chatbot with Auto-Generated IDs ---")
    print("Type 'new' to start a fresh session, 'exit' to quit.")

    # Generate a user ID once for this program run
    current_user_id = str(uuid.uuid4())
    print(f"Your User ID for this run: {current_user_id}")

    # Generate an initial session ID
    current_session_id = str(uuid.uuid4())
    print(f"Initial Session ID: {current_session_id}")

    while True:
        print(f"\n--- Current Session: {current_session_id}, User: {current_user_id} ---")
        action = input("Enter 'new' for a new session, 'chat' to continue, or 'exit' to quit: ").strip().lower()

        if action == "exit":
            print("Exiting program.")
            break
        elif action == "new":
            current_session_id = str(uuid.uuid4()) # Generate a new session ID
            print(f"Starting a new session. New Session ID: {current_session_id}")
            continue # Restart the outer loop to show new IDs and prompt for chat
        elif action == "chat":
            print("Type your message, or 'end' to go back to session menu, 'exit' to quit program.")
            while True: # Inner loop for continuous conversation within the same session/user
                user_query = input("You: ").strip()

                if user_query.lower() == "end":
                    print("Ending current chat session.")
                    break # Break out of the inner loop to go back to the session menu
                if user_query.lower() == "exit":
                    action = "exit" # Set outer loop condition to exit
                    break # Break out of inner loop

                try:
                    response = runnable_with_history.invoke(
                        {"question": user_query},
                        config={"configurable": {"session_id": current_session_id, "user_id": current_user_id}}
                    )
                    print(f"AI: {response}")
                except Exception as e:
                    print(f"AI: An error occurred while processing your request: {e}")

            if action == "exit": # Check if the user wanted to exit the program entirely
                break
        else:
            print("Invalid input. Please type 'new', 'chat', or 'exit'.")

    print("Goodbye!")