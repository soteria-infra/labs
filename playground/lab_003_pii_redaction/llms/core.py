import os
import shutil
from llms.query import query
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMP_FOLDER = os.getenv('TEMP_FOLDER', './_temp')
os.makedirs(TEMP_FOLDER, exist_ok=True)

def upload_to_temp(file_path: str) -> str:
    """
    Copies a file to a temporary location and returns the path to the copied file.
    """
    if not os.path.exists(file_path):
        print(f"Source file not found: {file_path}")
        raise FileNotFoundError(f"Source file not found: {file_path}")

    file_name = os.path.basename(file_path)
    destination_path = os.path.join(TEMP_FOLDER, file_name)

    try:
        shutil.copy(file_path, destination_path)
        print(f"File '{file_name}' copied to temporary location: {destination_path}")
        return destination_path
    except IOError as e:
        print(f"Error copying file '{file_name}' to '{destination_path}': {e}")
        raise IOError(f"Failed to copy file: {e}")
    
def query_db(user_query: str) -> dict:
    """
    Performs a query against the vector database.
    """
    if not user_query:
        print("No query string provided.")
        return {"success": False, "error": "Query parameter is missing"}

    try:
        response = query(user_query)
        
        # Handle different response types from the query function
        if isinstance(response, str):
            # If query returns a string, treat it as the result content
            print(f"Query processed successfully for: '{user_query}'")
            return {
                "success": True, 
                "message": "Query successful", 
                "results": [{"score": 1.0, "document": response}]
            }
        elif isinstance(response, dict):
            # If query returns a dict, handle it as before
            if response and response.get("found", False):
                print(f"Query processed successfully for: '{user_query}'")
                return {"success": True, "message": "Query successful", "results": response.get("results", [])}
            else:
                print(f"No results found for query: '{user_query}'")
                return {"success": True, "message": "No results found", "results": []}
        elif isinstance(response, list):
            # If query returns a list of results
            print(f"Query processed successfully for: '{user_query}'")
            results = []
            for i, item in enumerate(response):
                if isinstance(item, str):
                    results.append({"score": 1.0, "document": item})
                elif isinstance(item, dict):
                    results.append(item)
                else:
                    results.append({"score": 1.0, "document": str(item)})
            return {"success": True, "message": "Query successful", "results": results}
        else:
            # Handle any other response type
            print(f"No results found for query: '{user_query}'")
            return {"success": True, "message": "No results found", "results": []}
            
    except Exception as e:
        logger.error(f"An error occurred during database query for '{user_query}': {e}", exc_info=True)
        print(f"An error occurred during database query for '{user_query}': {e}")
        return {"success": False, "error": f"Internal error during query: {e}"}
   
def query_chat_processing_fn(context: str, user_input: str) -> str:
    """
    Processes user input as a query to the vector database.
    The 'context' here is the accumulated chat history,
    but `perform_db_query` doesn't directly use it for retrieval.
    It's maintained for the overall chat flow.
    """
    try:
        print("Chatbot: Searching...")
        query_response = query_db(user_input)

        if query_response["success"]:
            if query_response["results"]:
                response_text = "Here's what I found:\n\n"
                for i, res in enumerate(query_response["results"]):
                    score = res.get('score', 'N/A')
                    score_str = f"{score:.2f}" if isinstance(score, (int, float)) else str(score)
                    document = res.get('document', 'N/A')
                    
                    # Show more of the document content for better answers
                    if len(str(document)) > 500:
                        document_preview = str(document)[:500] + "..."
                    else:
                        document_preview = str(document)
                    
                    response_text += f"Result {i+1} (Score: {score_str}):\n{document_preview}\n\n"
                
                print(f"Chatbot: {response_text.strip()}")
                # For context, just store a summary
                context_summary = f"Found {len(query_response['results'])} relevant results"
            else:
                print("Chatbot: No matching results found for your query.")
                response_text = "No matching results found for your query."
                context_summary = response_text
        else:
            error_msg = f"Sorry, I encountered an error trying to search: {query_response['error']}"
            print(f"Chatbot: {error_msg}")
            response_text = error_msg
            context_summary = "Search error occurred"

        context += f"\nUser: {user_input}\nChatbot: {context_summary}"
        
    except Exception as e:
        error_msg = f"Sorry, I encountered an error trying to respond: {e}"
        print(f"Chatbot: {error_msg}")
        context += f"\nUser: {user_input}\nChatbot: Error: {e}"
        
    return context