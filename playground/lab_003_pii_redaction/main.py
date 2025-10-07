from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    WebSocket,
    UploadFile,
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from custom_loggers import DEFAULT_LOGGER
from websocket.handler import handle_websocket as do_handle_websocket
from api_handlers import handle_document_upload as do_handle_document_upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.TEMP_FOLDER.mkdir(exist_ok=True)
    yield
    # Clean up here...
    # TODO: might cleanup temp folder on server shutdown


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")


@app.post("/upload-document/")
async def handle_document_upload(
    file: UploadFile,
):
    return await do_handle_document_upload(file)


@app.websocket("/ws")
async def handle_websocket(websocket: WebSocket):
    await do_handle_websocket(websocket)


if __name__ == "__main__":
    import uvicorn

    # The 'llms.cli.get_conversation_handle_fn' and 'handle_conversation()' are
    # typically for CLI-based interaction and should not be mixed with the FastAPI web app.
    # The main FastAPI application should be run using uvicorn.
    DEFAULT_LOGGER.debug("Starting FastAPI application...")
    # This assumes your 'llms' package has properly initialized the vector DB, etc.
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
