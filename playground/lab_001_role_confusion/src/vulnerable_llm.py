from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate 

template = """
Answer the question below based on our conversation history

Conversation History: 
{context}

Question: 
{question}

Answer:
"""


# Initialize the model (ensure model is running)
try:
    model = OllamaLLM(model="llama3.2")
except Exception as e:
    print(f"Error Initializing the LLM.")
    print(f"Details: {e}")
    exit() # Exit if model can't be loaded

prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

def handle_conversation():
    context = "The conversation has just begun." # Start with a neutral context
    print("\n--- AI Chatbot (Powered by Llama3.2) ---")
    print("Ask me anything! Type 'exit' when you're done.")
    print("----------------------------------------")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("\n----------------------------------------")
            print("Llama3.2: Goodbye! Thanks for chatting.")
            print("----------------------------------------")
            break

        print("Llama3.2: Thinking...") 

        try:
            result = chain.invoke({"context": context, "question": user_input})
            print(f"Llama3.2: {result.strip()}")

            context += f"\nUser: {user_input}\nAI: {result.strip()}"
        
        except Exception as e:
            print(f"Llama3.2: Sorry, I encountered an error trying to respond. ({e})")
        
        print("----------------------------------------")

# if __name__ == "__main__":
#     handle_conversation()