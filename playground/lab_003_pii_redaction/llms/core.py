import shutil
from pathlib import Path
from typing import TypedDict, NotRequired

from config import settings
from llms.query import query

from custom_loggers import DEFAULT_LOGGER


class LLMResult(TypedDict):
    success: bool
    message: NotRequired[str]
    results: NotRequired[list]
    error: NotRequired[str]
    details: NotRequired["LLMResult"]


def upload_to_temp(file_path: Path) -> Path:
    """
    Copies a file to a temporary location and returns the path to the copied file.
    """
    if not file_path.exists():
        DEFAULT_LOGGER.debug(f"Source file not found: {file_path}")
        raise FileNotFoundError(f"Source file not found: {file_path}")

    file_name = file_path.name
    destination = settings.TEMP_FOLDER / file_name

    try:
        shutil.copy(file_path, destination)
        (
            DEFAULT_LOGGER.debug(
                f"File '{file_name}' copied to temporary location: {destination}"
            )
        )
        return destination
    except IOError as error:
        DEFAULT_LOGGER.error(
            f"Error copying file '{file_name}' to '{destination}': {error}"
        )
        raise error


def query_db(user_query: str) -> LLMResult:
    """
    Performs a query against the vector database.
    """
    if not user_query:
        DEFAULT_LOGGER.error("No query string provided.")
        return {"success": False, "error": "Query parameter is missing"}

    try:
        response = query(user_query)

        # Handle different response types from the query function
        if isinstance(response, str):
            # If query returns a string, treat it as the result content
            DEFAULT_LOGGER.debug(f"Query processed successfully for: '{user_query}'")
            return {
                "success": True,
                "message": "Query successful",
                "results": [{"score": 1.0, "document": response}],
            }
        elif isinstance(response, dict):
            # If query returns a dict, handle it as before
            if response and response.get("found", False):
                DEFAULT_LOGGER.debug(
                    f"Query processed successfully for: '{user_query}'"
                )
                return {
                    "success": True,
                    "message": "Query successful",
                    "results": response.get("results", []),
                }
            else:
                DEFAULT_LOGGER.debug(f"No results found for query: '{user_query}'")
                return {"success": True, "message": "No results found", "results": []}
        elif isinstance(response, list):
            # If query returns a list of results
            DEFAULT_LOGGER.debug(f"Query processed successfully for: '{user_query}'")
            results = []
            for item in response:
                if isinstance(item, str):
                    results.append({"score": 1.0, "document": item})
                elif isinstance(item, dict):
                    results.append(item)
                else:
                    results.append({"score": 1.0, "document": str(item)})
            return {"success": True, "message": "Query successful", "results": results}
        else:
            # Handle any other response type
            DEFAULT_LOGGER.error(f"No results found for query: '{user_query}'")
            return {"success": True, "message": "No results found", "results": []}

    except Exception as e:
        DEFAULT_LOGGER.error(
            f"An error occurred during database query for '{user_query}': {e}",
            exc_info=True,
        )
        DEFAULT_LOGGER.error(
            f"An error occurred during database query for '{user_query}': {e}"
        )
        return {"success": False, "error": f"Internal error during query: {e}"}


def query_chat_processing_fn(context: str, user_input: str) -> tuple[str, str]:
    """
    Processes user input as a query to the vector database.
    The 'context' here is the accumulated chat history,
    but `perform_db_query` doesn't directly use it for retrieval.
    It's maintained for the overall chat flow.
    """
    response_text = ""
    try:
        DEFAULT_LOGGER.debug("Chatbot: Searching...")
        query_response = query_db(user_input)

        if query_response["success"]:
            if results := query_response.get("results"):
                response_text = "Here's what I found:\n\n"
                for i, result in enumerate(results):
                    score = result.get("score", "N/A")
                    score_str = (
                        f"{score:.2f}"
                        if isinstance(score, (int, float))
                        else str(score)
                    )
                    document = result.get("document", "N/A")

                    # Show more of the document content for better answers
                    if len(str(document)) > 500:
                        document_preview = str(document)[:500] + "..."
                    else:
                        document_preview = str(document)

                    response_text += (
                        f"Result {i + 1} (Score: {score_str}):\n{document_preview}\n\n"
                    )

                DEFAULT_LOGGER.debug(f"Chatbot: {response_text.strip()}")
                # For context, just store a summary
                context_summary = (
                    f"Found {len(query_response['results'])} relevant results"
                )
            else:
                DEFAULT_LOGGER.debug(
                    "Chatbot: No matching results found for your query."
                )
                response_text = "No matching results found for your query."
                context_summary = response_text
        else:
            error_msg = f"Sorry, I encountered an error trying to search: {query_response['error']}"
            DEFAULT_LOGGER.debug(f"Chatbot: {error_msg}")
            response_text = error_msg
            context_summary = "Search error occurred"

        context += f"\nUser: {user_input}\nChatbot: {context_summary}"

    except Exception as e:
        error_msg = f"Sorry, I encountered an error trying to respond: {e}"
        DEFAULT_LOGGER.debug(f"Chatbot: {error_msg}")
        context += f"\nUser: {user_input}\nChatbot: Error: {e}"

    return context, response_text
