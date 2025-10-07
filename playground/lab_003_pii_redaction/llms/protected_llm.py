import os
import shutil
from pathlib import Path
import json

from config import settings
from llms.cli import get_conversation_handle_fn


from llms.core import query_chat_processing_fn, LLMResult
from llms.protected_embed import embed_file
from custom_loggers import DEFAULT_LOGGER


def process_and_embed_file_protected(file_path: Path) -> LLMResult:
    """
    Processes a file: saves it temporarily (if not already in temp),
    and then embeds it into the vector database.
    """
    if not file_path.exists():
        DEFAULT_LOGGER.debug(f"Input file not found: {file_path}")
        return {"success": False, "error": f"File not found: {file_path}"}

    filename = file_path.name
    temp_filepath = settings.TEMP_FOLDER / filename
    cleanup_temp_file = False

    try:
        if not file_path == temp_filepath:
            shutil.copy(file_path, temp_filepath)
            DEFAULT_LOGGER.debug(
                f"File '{filename}' copied temporarily to {temp_filepath}"
            )
            cleanup_temp_file = True
        else:
            DEFAULT_LOGGER.debug(
                f"File '{filename}' is already in temporary location: {temp_filepath}"
            )

        # Use the file path directly since embed() now handles string paths
        embedding_result = embed_file(temp_filepath)

        if embedding_result and embedding_result.get("success", True):
            DEFAULT_LOGGER.debug(f"File '{filename}' embedded successfully.")
            return {
                "success": True,
                "message": f"File '{filename}' embedded successfully",
                "details": embedding_result,
            }
        else:
            DEFAULT_LOGGER.debug(
                f"Embedding failed for file '{filename}'. Details: {embedding_result}"
            )
            return {
                "success": False,
                "error": f"Failed to embed file '{filename}'",
                "details": embedding_result,
            }

    except FileNotFoundError as e:
        DEFAULT_LOGGER.error(f"Error during file processing (FileNotFound): {e}")
        return {"success": False, "error": f"Server-side file error: {e}"}
    except IOError as e:
        DEFAULT_LOGGER.error(f"Error during file copy or cleanup (IOError): {e}")
        return {"success": False, "error": f"File system error: {e}"}
    except Exception as e:
        # Fixed: Use logging instead of print with exc_info
        DEFAULT_LOGGER.error(
            f"An unexpected error occurred during file processing and embedding: {e}",
            exc_info=True,
        )
        DEFAULT_LOGGER.error(
            f"An unexpected error occurred during file processing and embedding: {e}"
        )
        return {"success": False, "error": f"Internal error: {e}"}
    finally:
        if cleanup_temp_file and temp_filepath.exists():
            os.remove(temp_filepath)
            DEFAULT_LOGGER.debug(f"Temporary file '{temp_filepath}' removed.")


def run():
    file_to_embed_path = input(
        "Please enter the path to the file you want to embed (e.g., 'my_document.json'): "
    )
    file_to_embed_path = Path(file_to_embed_path.strip())

    if not file_to_embed_path:
        DEFAULT_LOGGER.error("No file path provided. Exiting.")
        return

    if not file_to_embed_path.exists():
        DEFAULT_LOGGER.debug(
            f"File not found at '{file_to_embed_path}'. Please check the path and try again. Exiting."
        )
        return

    # Check if it's a JSON file
    if not file_to_embed_path.suffix.endswith(".json"):
        DEFAULT_LOGGER.error(
            f"Only JSON files are supported. '{file_to_embed_path}' is not a JSON file. Exiting."
        )
        return

    # Validate that it's actually valid JSON
    try:
        with open(file_to_embed_path, "r", encoding="utf-8") as f:
            json.load(f)
        DEFAULT_LOGGER.debug(f"✓ Valid JSON file detected: {file_to_embed_path}")
    except json.JSONDecodeError as e:
        DEFAULT_LOGGER.debug(
            f"✗ Invalid JSON file: {e}. Please check the file format. Exiting."
        )
        return
    except Exception as e:
        DEFAULT_LOGGER.error(f"✗ Error reading file: {e}. Exiting.")
        return

    DEFAULT_LOGGER.debug(f"Attempting to embed file: {file_to_embed_path}")
    embed_result = process_and_embed_file_protected(file_to_embed_path)

    if embed_result["success"]:
        DEFAULT_LOGGER.debug(
            "✓ File embedded successfully. Now starting conversation mode."
        )
        DEFAULT_LOGGER.debug(
            "You can now ask questions about the content of your JSON file!"
        )
        DEFAULT_LOGGER.debug("Type 'quit' or 'exit' to end the conversation.")
        DEFAULT_LOGGER.debug("-" * 50)
        handle_conversation = get_conversation_handle_fn(query_chat_processing_fn)
        handle_conversation()
    else:
        DEFAULT_LOGGER.debug(
            f"✗ File embedding failed: {embed_result['error']}. Cannot proceed to conversation."
        )
        if "details" in embed_result and embed_result["details"]:
            DEFAULT_LOGGER.debug(f"Additional details: {embed_result['details']}")

    DEFAULT_LOGGER.debug("--- Workflow finished ---")


if __name__ == "__main__":
    run()
