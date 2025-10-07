import os
import json
from datetime import datetime
from pathlib import Path

from werkzeug.utils import secure_filename
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import settings
from llms.core import LLMResult
from llms.get_vector_db import get_vector_db
import soteria_sdk
from dotenv import load_dotenv

from llms.utils import clean_json_str
from custom_loggers import DEFAULT_LOGGER
from fastapi import UploadFile

load_dotenv()

# Configure Soteria SDK
DEFAULT_LOGGER.debug(f"Soteria API Key present: {bool(settings.SOTERIA_API_KEY)}")

if settings.SOTERIA_API_KEY:
    soteria_sdk.configure(
        api_key=settings.SOTERIA_API_KEY, api_base="https://api.soteriainfra.com"
    )
    DEFAULT_LOGGER.debug("Soteria SDK configured")
else:
    DEFAULT_LOGGER.warn("No Soteria API Key found!")


def allowed_file(filename: str) -> bool:
    """
    Checks if the file type is allowed for the given filename.
    """
    return Path(filename).suffix.lower() in {".json"}


def save_file(file: UploadFile) -> Path:
    """
    Saves the given uploaded file to disk and returns the path.
    """
    # Save the uploaded file with a secure filename and return the file path
    timestamp = datetime.now().timestamp()
    filename = f"{timestamp}_{secure_filename(file.filename)}"
    destination = settings.TEMP_FOLDER / filename
    file.save(
        destination
    )  # TODO: Verify i'm annotating with the right file type (why is save showing a warning)
    return destination


@soteria_sdk.guard_pii_redactor
def scan_pii_with_soteria(prompt: str) -> str:
    """
    Scan content for pii using Soteria SDK.
    This function MUST have a 'prompt' parameter for Soteria to work.
    """
    return prompt


def load_and_process_json(file_path: Path) -> list[Document] | None:
    """Load JSON file, scan for pii, and convert to documents"""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            raw_content = f.read()

        try:
            if settings.SOTERIA_API_KEY:
                scanned_content = scan_pii_with_soteria(prompt=raw_content)
            else:
                scanned_content = raw_content

        except soteria_sdk.SoteriaValidationError as e:
            raise ValueError(
                f"PII detected in file content, and redaction/policy failed: {e}"
            )
        except Exception:
            scanned_content = raw_content

        cleaned_json = clean_json_str(scanned_content)
        try:
            json_data = json.loads(cleaned_json)
        except json.JSONDecodeError:
            import re

            cleaned_content = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", cleaned_json)
            try:
                json_data = json.loads(cleaned_content)
            except json.JSONDecodeError as e2:
                DEFAULT_LOGGER.debug(f"Still cannot parse after cleaning: {e2}")
                return None

        # Convert to documents
        documents = []

        if isinstance(json_data, dict):
            content = json.dumps(json_data, indent=2, ensure_ascii=False)
            documents.append(
                Document(
                    page_content=content,
                    metadata={"source": file_path.as_posix(), "type": "json_object"},
                )
            )

        elif isinstance(json_data, list):
            for i, item in enumerate(json_data):
                if isinstance(item, (dict, list)):
                    content = json.dumps(item, indent=2, ensure_ascii=False)
                else:
                    content = str(item)
                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": file_path.as_posix(),
                            "item_index": i,
                            "type": "json_array_item",
                        },
                    )
                )

        else:
            content = str(json_data)
            documents.append(
                Document(
                    page_content=content,
                    metadata={"source": file_path.as_posix(), "type": "json_primitive"},
                )
            )
            DEFAULT_LOGGER.info("Created 1 document from JSON primitive")
            DEFAULT_LOGGER.debug("Created 1 document from JSON primitive")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=7500, chunk_overlap=100
        )
        chunks = text_splitter.split_documents(documents)

        return chunks

    except json.JSONDecodeError as e:
        DEFAULT_LOGGER.error(f"Invalid JSON in {file_path}: {e}")
        DEFAULT_LOGGER.error(f"JSON parse error: {e}")
        return None
    except ValueError as e:
        DEFAULT_LOGGER.error(f"Critical PII redaction issue for {file_path}: {e}")
        DEFAULT_LOGGER.error(f"Critical PII redaction issue: {e}")
        return None
    except Exception as e:
        DEFAULT_LOGGER.error(f"Error processing {file_path}: {e}", exc_info=True)
        DEFAULT_LOGGER.error(f"Processing error: {e}")
        return None


def embed_file_from_obj(file: UploadFile) -> LLMResult:
    """Handle embedding for file objects (Flask uploads)"""
    DEFAULT_LOGGER.debug(
        f"embed_file_object called with file: {file.filename if hasattr(file, 'filename') else 'unknown'}"
    )

    if file.filename != "" and file and allowed_file(file.filename):
        try:
            file_path = save_file(file)
            DEFAULT_LOGGER.debug(f"File saved to: {file_path}")

            chunks = load_and_process_json(file_path)

            if chunks is None:
                return {"success": False, "error": "Failed to load and process data"}

            DEFAULT_LOGGER.debug(f"Embedding {len(chunks)} chunks to vector DB...")
            db = get_vector_db()
            db.add_documents(chunks)

            # Remove persist() call if it's causing warnings
            try:
                db.persist()
            except:
                pass  # Ignore persistence warnings

            os.remove(file_path)
            DEFAULT_LOGGER.debug("File embedded successfully and temp file removed")

            return {"success": True, "message": "File embedded successfully"}
        except Exception as e:
            DEFAULT_LOGGER.debug(f"embed_file_object error: {e}")
            DEFAULT_LOGGER.error(f"Error in embed_file_object: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Invalid file or file type not allowed"}


def embed_file_from_path(file_path: Path) -> LLMResult:
    """Handle embedding for file paths (strings)"""
    DEFAULT_LOGGER.debug(f"embed_file_path called with: {file_path}")

    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    filename = os.path.basename(file_path)
    if not allowed_file(filename):
        return {
            "success": False,
            "error": "File type not allowed. Only JSON files are supported.",
        }

    try:
        chunks = load_and_process_json(file_path)

        if chunks is None:
            return {"success": False, "error": "Failed to load and process data"}

        DEFAULT_LOGGER.debug(f"Embedding {len(chunks)} chunks to vector DB...")
        db = get_vector_db()
        db.add_documents(chunks)

        # Remove persist() call if it's causing warnings
        try:
            db.persist()
        except:
            pass  # Ignore persistence warnings

        DEFAULT_LOGGER.debug("File embedded successfully")
        return {"success": True, "message": f"File '{filename}' embedded successfully"}

    except Exception as e:
        print(f"DEBUG: embed_file_path error: {e}")
        DEFAULT_LOGGER.error(f"Error in embed_file_path: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def embed_file(file: UploadFile | Path | str) -> LLMResult:
    """
    Universal embed function that handles both file objects and file paths
    """
    DEFAULT_LOGGER.debug(f"embed() called with type: {type(file)}")

    if hasattr(file, "filename"):
        # It's a file object (like from Flask upload)
        DEFAULT_LOGGER.debug("Detected file object, calling embed_file_object")
        return embed_file_from_obj(file)
    elif isinstance(file, str):
        # It's a file path string
        DEFAULT_LOGGER.debug("Detected file path string, calling embed_file_path")
        return embed_file_from_path(Path(file))
    elif isinstance(file, Path):
        return embed_file_from_path(file)
    else:
        error_msg = f"Invalid input type: {type(file)}, expected file object or file path string"
        DEFAULT_LOGGER.debug(f"{error_msg}")
        return {"success": False, "error": error_msg}
