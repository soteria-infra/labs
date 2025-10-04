import os
from datetime import datetime
from werkzeug.utils import secure_filename
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import settings
from llms.get_vector_db import get_vector_db

from custom_loggers import DEFAULT_LOGGER


# Function to check if the uploaded file is allowed
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"json"}


# Function to save the uploaded file to the temporary folder (for file objects)
def save_file(file):
    # Save the uploaded file with a secure filename and return the file path
    ct = datetime.now()
    ts = ct.timestamp()
    filename = str(ts) + "_" + secure_filename(file.filename)
    file_path = os.path.join(settings.TEMP_FOLDER, filename)
    file.save(file_path)
    return file_path


# Function to load and split the data from the JSON file
def load_and_split_data(file_path):
    try:
        DEFAULT_LOGGER.info(f"Loading JSON file: {file_path}")

        # Skip JSONLoader entirely and handle JSON manually for better control
        import json

        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Import Document class
        from langchain_core.documents import Document

        # Convert JSON to string format for text processing
        if isinstance(json_data, dict):
            # Convert dict to readable text
            content = json.dumps(json_data, indent=2, ensure_ascii=False)
            data = [
                Document(
                    page_content=content,
                    metadata={"source": file_path, "type": "json_object"},
                )
            ]
            DEFAULT_LOGGER.info(f"Processed JSON object with {len(content)} characters")

        elif isinstance(json_data, list):
            # Handle list of objects
            data = []
            for i, item in enumerate(json_data):
                if isinstance(item, (dict, list)):
                    content = json.dumps(item, indent=2, ensure_ascii=False)
                else:
                    content = str(item)
                data.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": file_path,
                            "item_index": i,
                            "type": "json_array_item",
                        },
                    )
                )
            DEFAULT_LOGGER.info(f"Processed JSON array with {len(data)} items")

        else:
            # Handle primitive types
            content = str(json_data)
            data = [
                Document(
                    page_content=content,
                    metadata={"source": file_path, "type": "json_primitive"},
                )
            ]
            DEFAULT_LOGGER.info(f"Processed JSON primitive: {type(json_data).__name__}")

        if not data:
            raise ValueError("No data could be loaded from the JSON file")

        DEFAULT_LOGGER.info(
            f"Created {len(data)} documents, now splitting into chunks..."
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=7500, chunk_overlap=100
        )
        chunks = text_splitter.split_documents(data)
        DEFAULT_LOGGER.info(f"Split into {len(chunks)} chunks")

        return chunks

    except json.JSONDecodeError as e:
        DEFAULT_LOGGER.error(f"Invalid JSON format in {file_path}: {e}")
        return None
    except Exception as e:
        DEFAULT_LOGGER.error(
            f"Error loading and splitting data from {file_path}: {e}", exc_info=True
        )
        return None


# Main function to handle the embedding process for file objects (Flask uploads)
def embed_file_object(file):
    """Handle embedding for file objects (like Flask uploads)"""
    if file.filename != "" and file and allowed_file(file.filename):
        try:
            file_path = save_file(file)
            chunks = load_and_split_data(file_path)

            if chunks is None:
                return {"success": False, "error": "Failed to load and split data"}

            db = get_vector_db()
            db.add_documents(chunks)
            db.persist()
            os.remove(file_path)

            return {"success": True, "message": "File embedded successfully"}
        except Exception as e:
            DEFAULT_LOGGER.error(f"Error in embed_file_object: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Invalid file or file type not allowed"}


# Main function to handle the embedding process for file paths (strings)
def embed_file_path(file_path):
    """Handle embedding for file paths (strings)"""
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    filename = os.path.basename(file_path)
    if not allowed_file(filename):
        return {
            "success": False,
            "error": "File type not allowed. Only JSON files are supported.",
        }

    try:
        chunks = load_and_split_data(file_path)

        if chunks is None:
            return {"success": False, "error": "Failed to load and split data"}

        db = get_vector_db()
        db.add_documents(chunks)
        db.persist()

        return {"success": True, "message": f"File '{filename}' embedded successfully"}
    except Exception as e:
        DEFAULT_LOGGER.error(f"Error in embed_file_path: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# Unified embed function that handles both file objects and file paths
def embed(file_or_path):
    """
    Universal embed function that handles both file objects and file paths
    """
    # Check if it's a file object (has filename attribute) or a string path
    if hasattr(file_or_path, "filename"):
        # It's a file object (like from Flask upload)
        return embed_file_object(file_or_path)
    elif isinstance(file_or_path, str):
        # It's a file path string
        return embed_file_path(file_or_path)
    else:
        return {
            "success": False,
            "error": "Invalid input: expected file object or file path string",
        }
