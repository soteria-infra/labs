from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
import soteria_sdk

soteria_sdk.configure(api_key="your-api-key", api_base="https://api.soteriainfra.com")

template = """
Answer the question below based on our conversation history
Conversation History:
{context}
Question:
{question}
Answer:
""" 

# Initialize the model
try:
    model = OllamaLLM(model="llama3.2")
except Exception as e:
    print(f"Error Initializing the LLM.")
    print(f"Details: {e}")
    exit()

prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

# This is the function that needs protection - it processes the user input
@soteria_sdk.guard_jailbreak  
def protected_llm_call(prompt: str):
    """
    Protected LLM call that blocks jailbreak attempts.
    """
    # Parse the prompt back into components for your chain
    lines = prompt.split('\n')
   
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
   
    context_text = '\n'.join(context_lines).strip()
    question_text = '\n'.join(question_lines).strip()
   
    # Call your original chain
    result = chain.invoke({"context": context_text, "question": question_text})
    return result.strip()

# This function handles the conversation flow - no decoration needed
def handle_conversation():
    context = "The conversation has just begun."
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
            full_prompt = f"""Answer the question below based on our conversation history
Conversation History:
{context}
Question:
{user_input}
Answer:"""
           
            # Use the protected function
            result = protected_llm_call(prompt=full_prompt)
            print(f"Llama3.2: {result}")
            context += f"\nUser: {user_input}\nAI: {result}"
           
        except soteria_sdk.SoteriaValidationError as e:
            print(f"Llama3.2: I can't process that request. Security filter activated.")
           
        except Exception as e:
            print(f"Llama3.2: Sorry, I encountered an error trying to respond. ({e})")
       
        print("----------------------------------------")

# if __name__ == "__main__":
#     handle_conversation()