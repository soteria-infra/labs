from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import uuid
from typing import Dict
import uvicorn
import soteria_sdk

from llms.protected_llm import protected_chat_handler
from llms.vulnerable_llm import runnable_with_history_vulnerable

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

class ConnectionState:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())   
        self.protection_mode = True        


connection_states: Dict[WebSocket, ConnectionState] = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state = ConnectionState()
    connection_states[websocket] = state

    print(f"New WebSocket connection established. Session ID: {state.session_id}, User ID: {state.user_id}")
    await websocket.send_text(f"Mode switched to: {'protected' if state.protection_mode else 'vulnerable'}")


    try:
        while True:
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)

                if message_data.get("type") == "toggle":
                    state.protection_mode = message_data.get("protected", True)
                    mode = "protected" if state.protection_mode else "vulnerable"
                    await websocket.send_text(f"Mode switched to: {mode}")
                    continue

                elif message_data.get("type") == "chat":
                    user_input = message_data.get("message", "")
                else:
                    user_input = data
            except json.JSONDecodeError:
                user_input = data

            if not user_input.strip():
                continue

            result = ""

            if state.protection_mode:
                try:
                    result = protected_chat_handler(
                        prompt=user_input,
                        session_id=state.session_id,
                        user_id=state.user_id
                    )
                except soteria_sdk.SoteriaValidationError as e:
                    result = f"AI: I can't process that request. Security filter activated. Details: {e}"
                except Exception as e:
                    result = f"Sorry, I encountered an error in protected mode: {e}"
            else:
                if runnable_with_history_vulnerable is None:
                    result = "LLM service for vulnerable mode is unavailable due to an initialization error."
                else:
                    try:
                        llm_response = runnable_with_history_vulnerable.invoke(
                            {"question": user_input},
                            config={"configurable": {"session_id": state.session_id, "user_id": state.user_id}}
                        )
                        result = llm_response.strip()
                    except Exception as e:
                        result = f"Sorry, I encountered an error in vulnerable mode: {e}"

            await websocket.send_text(result)

    except WebSocketDisconnect:
        print(f"WebSocket disconnected. Session ID: {state.session_id}, User ID: {state.user_id}")
        if websocket in connection_states:
            del connection_states[websocket]
    except Exception as e:
        print(f"An unexpected error occurred in WebSocket connection (Session ID: {state.session_id}, User ID: {state.user_id}): {e}")
        try:
            await websocket.send_text(f"Server error: {e}")
        except RuntimeError:
            pass
        if websocket in connection_states:
            del connection_states[websocket]

if __name__ == "__main__":
    print("Starting FastAPI chat server...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)