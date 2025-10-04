import os
import logging
from dotenv import load_dotenv
import shutil

from llms.cli import get_conversation_handle_fn

load_dotenv()

from llms.core import query_chat_processing_fn
from llms.protected_embed import TEMP_FOLDER, embed


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def process_and_embed_file_protected(file_path: str) -> dict:
    """
    Processes a file: saves it temporarily (if not already in temp),
    and then embeds it into the vector database.
    """
    if not os.path.exists(file_path):
        print(f"Input file not found: {file_path}")
        return {"success": False, "error": f"File not found: {file_path}"}

    filename = os.path.basename(file_path)
    temp_filepath = os.path.join(TEMP_FOLDER, filename)
    cleanup_temp_file = False

    try:
        if not os.path.abspath(file_path) == os.path.abspath(temp_filepath):
            shutil.copy(file_path, temp_filepath)
            print(f"File '{filename}' copied temporarily to {temp_filepath}")
            cleanup_temp_file = True
        else:
            print(f"File '{filename}' is already in temporary location: {temp_filepath}")

        # Use the file path directly since embed() now handles string paths
        embedding_result = embed(temp_filepath)

        if embedding_result and embedding_result.get("success", True):
            print(f"File '{filename}' embedded successfully.")
            return {"success": True, "message": f"File '{filename}' embedded successfully", "details": embedding_result}
        else:
            print(f"Embedding failed for file '{filename}'. Details: {embedding_result}")
            return {"success": False, "error": f"Failed to embed file '{filename}'", "details": embedding_result}

    except FileNotFoundError as e:
        print(f"Error during file processing (FileNotFound): {e}")
        return {"success": False, "error": f"Server-side file error: {e}"}
    except IOError as e:
        print(f"Error during file copy or cleanup (IOError): {e}")
        return {"success": False, "error": f"File system error: {e}"}
    except Exception as e:
        # Fixed: Use logging instead of print with exc_info
        logger.error(f"An unexpected error occurred during file processing and embedding: {e}", exc_info=True)
        print(f"An unexpected error occurred during file processing and embedding: {e}")
        return {"success": False, "error": f"Internal error: {e}"}
    finally:
        if cleanup_temp_file and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            print(f"Temporary file '{temp_filepath}' removed.")


def run():
    file_to_embed_path = input("Please enter the path to the file you want to embed (e.g., 'my_document.json'): ")
    file_to_embed_path = file_to_embed_path.strip()

    if not file_to_embed_path:
        print("No file path provided. Exiting.")
        return

    if not os.path.exists(file_to_embed_path):
        print(f"File not found at '{file_to_embed_path}'. Please check the path and try again. Exiting.")
        return

    # Check if it's a JSON file
    if not file_to_embed_path.lower().endswith('.json'):
        print(f"Only JSON files are supported. '{file_to_embed_path}' is not a JSON file. Exiting.")
        return

    # Validate that it's actually valid JSON
    try:
        import json
        with open(file_to_embed_path, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"✓ Valid JSON file detected: {file_to_embed_path}")
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON file: {e}. Please check the file format. Exiting.")
        return
    except Exception as e:
        print(f"✗ Error reading file: {e}. Exiting.")
        return

    print(f"Attempting to embed file: {file_to_embed_path}")
    embed_result = process_and_embed_file_protected(file_to_embed_path)
    

    if embed_result["success"]:
        print("✓ File embedded successfully. Now starting conversation mode.")
        print("You can now ask questions about the content of your JSON file!")
        print("Type 'quit' or 'exit' to end the conversation.")
        print("-" * 50)
        handle_conversation = get_conversation_handle_fn(query_chat_processing_fn)
        handle_conversation()
    else:
        print(f"✗ File embedding failed: {embed_result['error']}. Cannot proceed to conversation.")
        if 'details' in embed_result and embed_result['details']:
            print(f"Additional details: {embed_result['details']}")
   
    print("--- Workflow finished ---")

if __name__ == "__main__":
    run()

