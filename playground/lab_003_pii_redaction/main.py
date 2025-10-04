import os
import shutil

from pydantic import ValidationError

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    HTTPException,
    status,
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from llms.core import TEMP_FOLDER
from llms import protected_llm, vulnerable_llm
from websocket_primitives import WSMessage, WSToggleMessage, WSChatMessage
from custom_loggers import DEFAULT_LOGGER, WS_LOGGER, LLM_LOGGER

contexts: dict[WebSocket, str] = {}
protection_modes: dict[WebSocket, bool] = {}


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")


@app.post("/upload-document/")
async def upload_document_endpoint(
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
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    temp_file_path = os.path.join(TEMP_FOLDER, file.filename)

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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Handles WebSocket connections, allowing clients to send chat messages
    and receive intelligent responses based on the embedded knowledge base.
    """
    await websocket.accept()
    # Initialize an empty conversational context for this new client connection
    contexts[websocket] = "The conversation has just begun."
    protection_modes[websocket] = True  # Default to protected

    try:
        while True:
            raw_data = await websocket.receive_text()
            WS_LOGGER.debug(f"Received raw_data: {raw_data}")

            message_root = None
            try:
                message_wrapper = WSMessage.model_validate_json(raw_data)
                message_root = message_wrapper.root
            except ValidationError as e:
                WS_LOGGER.debug(
                    f"ValidationError for raw_data: {raw_data} - {e}. Skipping LLM call due to invalid message format."
                )
                # Send an error back to the client if the message format is invalid
                await websocket.send_text("System: Invalid message format received.")
                continue

            # Now, check the type of message_root
            if isinstance(message_root, WSToggleMessage):
                await handle_ws_toggle_message(
                    websocket, message_root
                )  # Pass the actual WSToggleMessage
                WS_LOGGER.debug(
                    f"Processed toggle for {websocket.client.host}:{websocket.client.port}. Protection mode is now:"
                    f" {protection_modes.get(websocket)}. Executing continue, skipping run_llm."
                )
                continue

            elif isinstance(message_root, WSChatMessage):
                user_input = message_root.message.strip()
                if not user_input:
                    WS_LOGGER.debug(
                        f"Received empty chat message for {websocket.client.host}:{websocket.client.port}. "
                        "Skipping LLM call."
                    )
                    continue

                WS_LOGGER.debug(
                    f"Calling run_llm for a WSChatMessage from {websocket.client.host}:{websocket.client.port}."
                )
                # run_llm is now async
                result = await run_llm(websocket, user_input)
                await websocket.send_text(result)

            elif isinstance(
                message_root, str
            ):  # Handle plain string messages if that's still desired
                user_input = message_root.strip()
                if not user_input:
                    WS_LOGGER.debug(
                        f"Received empty string message for {websocket.client.host}:{websocket.client.port}. "
                        "Skipping LLM call."
                    )
                    continue

                WS_LOGGER.debug(
                    f"Calling run_llm for a raw string message from {websocket.client.host}:{websocket.client.port}."
                )
                # run_llm is now async
                result = await run_llm(websocket, user_input)
                await websocket.send_text(result)

            else:
                # Fallback for unexpected but valid WSMessage types that aren't WSToggleMessage or WSChatMessage or str
                WS_LOGGER.debug(
                    f"Received unhandled valid WSMessage root type: {type(message_root)} from "
                    f"{websocket.client.host}:{websocket.client.port}. Skipping."
                )
                await websocket.send_text("System: Unhandled message type.")
                continue

    except WebSocketDisconnect:
        WS_LOGGER.debug(
            f"WebSocket disconnected for {websocket.client.host}:{websocket.client.port}"
        )
        if websocket in contexts:
            del contexts[websocket]
        if websocket in protection_modes:
            del protection_modes[websocket]
    except Exception as e:
        DEFAULT_LOGGER.error(
            f"WebSocket error for {websocket.client.host}:{websocket.client.port}: {e}",
            exc_info=True,
        )


async def handle_ws_toggle_message(websocket: WebSocket, message: WSToggleMessage):
    protection_modes[websocket] = message.protected
    mode = "protected" if protection_modes[websocket] else "vulnerable"
    WS_LOGGER.debug(
        f"[WS_DEBUG] Inside handle_ws_toggle_message: Protection mode set to {protection_modes[websocket]} "
        f"for {websocket.client.host}:{websocket.client.port}"
    )
    await websocket.send_text(f"Mode switched to: {mode}")


# Modified run_llm to be asynchronous and directly use query_chat_processing_fn
async def run_llm(websocket: WebSocket, user_input: str) -> str:
    """
    Processes a user's chat message using the appropriate LLM based on protection mode.
    """
    current_context = contexts.get(websocket, "The conversation has just begun.")
    current_protection_mode = protection_modes.get(
        websocket, True
    )  # Defaults to `protected`

    LLM_LOGGER.debug(
        f"Calling run_llm for {websocket.client.host}:{websocket.client.port}"
    )
    LLM_LOGGER.debug(f"User input: '{user_input}'")
    LLM_LOGGER.debug(f"Resolved protection_mode: {current_protection_mode}")
    LLM_LOGGER.debug(
        f"Current context: '{current_context[:100]}...'"
    )  # Log the first 100 chars of context

    # Select the correct LLM based on the protection mode
    llm_processor = (
        protected_llm.query_chat_processing_fn
        if current_protection_mode
        else vulnerable_llm.query_chat_processing_fn
    )

    try:
        # Call the LLM processing function
        DEFAULT_LOGGER.debug(f"llm_processor -> {llm_processor}")
        new_context, llm_response = llm_processor(
            current_context, user_input
        )  # Await the async function

        # Update the context for the next turn
        contexts[websocket] = new_context
        return llm_response
    except Exception as e:
        DEFAULT_LOGGER.error(
            f"Error during LLM processing for input '{user_input}': {e}", exc_info=True
        )
        return "System: An error occurred while processing your request."


if __name__ == "__main__":
    import uvicorn

    # The 'llms.cli.get_conversation_handle_fn' and 'handle_conversation()' are
    # typically for CLI-based interaction and should not be mixed with the FastAPI web app.
    # The main FastAPI application should be run using uvicorn.
    DEFAULT_LOGGER.debug("Starting FastAPI application...")
    # This assumes your 'llms' package has properly initialized the vector DB, etc.
    uvicorn.run(app, host="0.0.0.0", port=8000)
