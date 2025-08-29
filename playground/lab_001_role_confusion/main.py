from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse # Added import for FileResponse
import json
from typing import Dict
import uvicorn
import soteria_sdk # Import soteria_sdk for error handling

# Import the separate implementations' specific functions/objects
# We need to import the module as a whole to access its top-level variables (template, chain)
from tests import protected_llm
from tests import vulnerable_llm


app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

# Store contexts for each connection
contexts: Dict[WebSocket, str] = {}
protection_modes: Dict[WebSocket, bool] = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    contexts[websocket] = "The conversation has just begun."
    protection_modes[websocket] = True  # Default to protected
   
    try:
        while True:
            data = await websocket.receive_text()
           
            try:
                message_data = json.loads(data)
               
                if message_data.get("type") == "toggle":
                    # Toggle protection mode
                    protection_modes[websocket] = message_data.get("protected", True)
                    mode = "protected" if protection_modes[websocket] else "vulnerable"
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
               
            context = contexts[websocket]
            result = "" # Initialize result

            # Use the appropriate implementation
            if protection_modes[websocket]:
                try:
                    # Construct the full prompt string for the protected LLM
                    full_prompt = protected_llm.template.format(context=context, question=user_input)
                    result = protected_llm.protected_llm_call(prompt=full_prompt)
                except soteria_sdk.SoteriaValidationError:
                    result = "I can't process that request. Security filter activated."
                except Exception as e:
                    result = f"Sorry, I encountered an error in protected mode: {e}"
            else:
                try:
                    # Directly invoke the vulnerable chain
                    llm_response = vulnerable_llm.chain.invoke({"context": context, "question": user_input})
                    result = llm_response.strip()
                except Exception as e:
                    result = f"Sorry, I encountered an error in vulnerable mode: {e}"
           
            # Update context
            contexts[websocket] += f"\nUser: {user_input}\nAI: {result}"
           
            await websocket.send_text(result)
               
    except WebSocketDisconnect:
        if websocket in contexts:
            del contexts[websocket]
        if websocket in protection_modes:
            del protection_modes[websocket]

if __name__ == "__main__":
    print("Starting FastAPI chat server...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8000)