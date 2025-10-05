import os
import shutil

from fastapi import status, HTTPException, UploadFile

from config import settings
from custom_loggers import DEFAULT_LOGGER
from llms import protected_llm, vulnerable_llm
from websocket.handler import protection_modes


async def handle_document_upload(
    file: UploadFile,
):  # Make this async for better FastAPI integration
    """
    Handles document uploads via HTTP POST. The uploaded JSON file is saved temporarily,
    embedded into the vector database, and then deleted.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded."
        )

    # Ensure the TEMP_FOLDER exists
    os.makedirs(settings.TEMP_FOLDER, exist_ok=True)
    temp_file_path = os.path.join(settings.TEMP_FOLDER, file.filename)

    try:
        # Save the uploaded file temporarily
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        is_protected = True
        if protection_modes:
            is_protected = list(protection_modes.values())[-1]

        DEFAULT_LOGGER.debug(
            f"Processing file '{file.filename}' with protection mode: {is_protected}"
        )

        if is_protected:
            embedding_result = protected_llm.process_and_embed_file_protected(
                temp_file_path
            )
        else:
            embedding_result = vulnerable_llm.process_and_embed_file(temp_file_path)

        if not embedding_result["success"]:
            detail_message = embedding_result.get("error", "Embedding failed")
            if embedding_result.get("details"):
                detail_message += f" Details: {embedding_result['details']}"
            DEFAULT_LOGGER.debug(f"Document embedding failed: {detail_message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail_message
            )

        DEFAULT_LOGGER.debug(
            f"Document '{file.filename}' uploaded and embedded successfully."
        )
        return {
            "filename": file.filename,
            "message": "File uploaded and embedded successfully.",
        }
    except HTTPException:
        raise  # Re-raise HTTPExceptions
    except Exception as e:
        DEFAULT_LOGGER.error(
            f"An unexpected error occurred during file upload or embedding for '{file.filename}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file '{file.filename}': {e}",
        )
    finally:
        # Ensure the temporary file is removed after processing.
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                DEFAULT_LOGGER.debug(f"Temporary file '{temp_file_path}' removed.")
            except Exception as e:
                DEFAULT_LOGGER.error(
                    f"Error removing temporary file '{temp_file_path}': {e}"
                )
