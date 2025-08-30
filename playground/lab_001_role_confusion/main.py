from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse  # Added import for FileResponse
import soteria_sdk  # Import soteria_sdk for error handling
from pydantic import ValidationError

# Import the separate implementations' specific functions/objects
# We need to import the module as a whole to access its top-level variables (template, chain)
from llms import protected_llm, vulnerable_llm, DEFAULT_CHAT_TEMPLATE
from websocket_primitives import WSMessage, WSToggleMessage, WSChatMessage


# Store contexts for each connection
contexts: dict[WebSocket, str] = {}
protection_modes: dict[WebSocket, bool] = {}

app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    contexts[websocket] = "The conversation has just begun."
    protection_modes[websocket] = True  # Default to protected

    try:
        while True:
            raw_data = await websocket.receive_text()
            user_input = ""
            try:
                message = WSMessage.model_validate_json(raw_data)
                if isinstance(message, WSToggleMessage):
                    await handle_ws_toggle_message(websocket, message)
                    continue
                if isinstance(message, WSChatMessage):
                    user_input = message.message
                if isinstance(message, str):
                    user_input = message.strip()
                    if not user_input:
                        continue
            except ValidationError:
                continue
            result = run_llm(websocket, user_input)
            await websocket.send_text(result)
    except WebSocketDisconnect:
        if websocket in contexts:
            del contexts[websocket]
        if websocket in protection_modes:
            del protection_modes[websocket]


async def handle_ws_toggle_message(websocket: WebSocket, message: WSToggleMessage):
    protection_modes[websocket] = message.protected
    mode = "protected" if protection_modes[websocket] else "vulnerable"
    await websocket.send_text(f"Mode switched to: {mode}")


def run_llm(websocket: WebSocket, user_input: str) -> str:
    context = contexts[websocket]
    result = ""  # Initialize result

    # Use the appropriate implementation
    if protection_modes[websocket]:
        try:
            # Construct the full prompt string for the protected LLM
            full_prompt = DEFAULT_CHAT_TEMPLATE.format(
                context=context, question=user_input
            )
            result = protected_llm.protected_llm_call(prompt=full_prompt)
        except soteria_sdk.SoteriaValidationError:
            result = "I can't process that request. Security filter activated."
        except Exception as error:
            result = f"Sorry, I encountered an error in protected mode: {error}"
    else:
        try:
            # Directly invoke the vulnerable chain
            llm_response = vulnerable_llm.chain.invoke(
                {"context": context, "question": user_input}
            )
            result = llm_response.strip()
        except Exception as error:
            result = f"Sorry, I encountered an error in vulnerable mode: {error}"
    return result
