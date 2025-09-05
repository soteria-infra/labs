from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import soteria_sdk
from pydantic import ValidationError

# Import the separate implementations' specific functions/objects
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
            print(f"[WS_DEBUG] Received raw_data: {raw_data}")

            message_root = None # This will hold the actual message object (WSToggleMessage, WSChatMessage, or str)
            try:
                # Validate the raw data into the WSMessage RootModel wrapper
                message_wrapper = WSMessage.model_validate_json(raw_data)
                # Extract the actual message from the RootModel
                message_root = message_wrapper.root 
            except ValidationError as e:
                print(f"[WS_DEBUG] ValidationError for raw_data: {raw_data} - {e}. Skipping LLM call due to invalid message format.")
                continue

            # Now, check the type of message_root
            if isinstance(message_root, WSToggleMessage):
                await handle_ws_toggle_message(websocket, message_root) # Pass the actual WSToggleMessage
                print(f"[WS_DEBUG] Processed toggle for {websocket.client.host}:{websocket.client.port}. Protection mode is now: {protection_modes.get(websocket)}. Executing continue, skipping run_llm.")
                continue
            
            elif isinstance(message_root, WSChatMessage):
                user_input = message_root.message.strip()
                if not user_input:
                    print(f"[WS_DEBUG] Received empty chat message for {websocket.client.host}:{websocket.client.port}. Skipping LLM call.")
                    continue
                
                print(f"[WS_DEBUG] Calling run_llm for a WSChatMessage from {websocket.client.host}:{websocket.client.port}.")
                result = run_llm(websocket, user_input)
                await websocket.send_text(result)
            
            elif isinstance(message_root, str): # Handle plain string messages if that's still desired
                user_input = message_root.strip()
                if not user_input:
                    print(f"[WS_DEBUG] Received empty string message for {websocket.client.host}:{websocket.client.port}. Skipping LLM call.")
                    continue
                
                print(f"[WS_DEBUG] Calling run_llm for a raw string message from {websocket.client.host}:{websocket.client.port}.")
                result = run_llm(websocket, user_input)
                await websocket.send_text(result)

            else:
                # Fallback for unexpected but valid WSMessage types that aren't WSToggleMessage or WSChatMessage or str
                print(f"[WS_DEBUG] Received unhandled valid WSMessage root type: {type(message_root)} from {websocket.client.host}:{websocket.client.port}. Skipping.")
                continue

    except WebSocketDisconnect:
        print(f"[WS_DEBUG] WebSocket disconnected for {websocket.client.host}:{websocket.client.port}")
        if websocket in contexts:
            del contexts[websocket]
        if websocket in protection_modes:
            del protection_modes[websocket]


async def handle_ws_toggle_message(websocket: WebSocket, message: WSToggleMessage):
    protection_modes[websocket] = message.protected
    mode = "protected" if protection_modes[websocket] else "vulnerable"
    print(f"[WS_DEBUG] Inside handle_ws_toggle_message: Protection mode set to {protection_modes[websocket]} for {websocket.client.host}:{websocket.client.port}")
    await websocket.send_text(f"Mode switched to: {mode}")


# (The run_llm function remains the same as your last provided version,
#  including the detailed logging I added for it)
def run_llm(websocket: WebSocket, user_input: str) -> str:
    context = contexts[websocket]
    result = ""

    current_protection_mode = protection_modes.get(websocket, True)

    print(f"[LLM_DEBUG] Calling run_llm for {websocket.client.host}:{websocket.client.port}")
    print(f"[LLM_DEBUG]   User input: '{user_input}'")
    print(f"[LLM_DEBUG]   Resolved protection_mode: {current_protection_mode}")

    if current_protection_mode:
        try:
            full_prompt = DEFAULT_CHAT_TEMPLATE.format(
                context=context, question=user_input
            )
            print(f"[LLM_DEBUG]   Entering PROTECTED branch.")
            print(f"[LLM_DEBUG]   Prompt to protected_llm_call: '{full_prompt[:200]}'...")
            result = protected_llm.protected_llm_call(prompt=full_prompt)
            print(f"[LLM_DEBUG]   protected_llm_call successful.")
        except soteria_sdk.SoteriaValidationError as e:
            print(f"[LLM_DEBUG]   SoteriaValidationError caught in protected branch: {e}")
            result = "I can't process that request. Security filter activated."
        except Exception as error:
            print(f"[LLM_DEBUG]   Generic Exception in protected branch: {error}")
            result = f"Sorry, I encountered an error in protected mode: {error}"
    else:
        try:
            print(f"[LLM_DEBUG]   Entering VULNERABLE branch.")
            llm_response = vulnerable_llm.chain.invoke(
                {"context": context, "question": user_input}
            )
            result = llm_response.strip()
            print(f"[LLM_DEBUG]   vulnerable_llm.chain.invoke successful.")
        except Exception as error:
            print(f"[LLM_DEBUG]   Generic Exception in vulnerable branch: {error}")
            result = f"Sorry, I encountered an error in vulnerable mode: {error}"
    print(f"[LLM_DEBUG] run_llm finished. Resulting message: '{result[:200]}'...")
    return result