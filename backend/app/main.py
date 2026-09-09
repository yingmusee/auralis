import asyncio
import os
import logging
from typing import List, Optional, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db, insert_transcription, get_all_transcriptions, search_transcriptions
from app.storage import save_upload_file, ensure_upload_dir
from app.transcriber import get_transcriber

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("auralis.api")

def get_allowed_origins() -> List[str]:
    """Return configured browser origins, with local development defaults."""
    configured_origins = os.environ.get("ALLOWED_ORIGINS")
    if configured_origins:
        return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://localhost:5173"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database and uploads folder
    logger.info("Initializing database...")
    init_db()
    ensure_upload_dir()
    logger.info("Pre-warming Whisper transcriber...")
    get_transcriber().load_model()
    logger.info("Application startup complete.")
    yield
    # Shutdown
    logger.info("Application shutting down.")

app = FastAPI(
    title="Auralis Speech-to-Text API",
    description="RESTful API for speech recognition using Whisper-tiny and SQLite",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration to support frontend SPA
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", summary="API Information")
def api_information():
    """Provides a useful response at the API base URL."""
    return {
        "service": "Auralis Speech-to-Text API",
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
    }

@app.get("/health", summary="Health Check")
def health_check():
    """Returns the status of the service."""
    return {"status": "ok"}

@app.post("/transcribe", summary="Transcribe Audio")
async def transcribe(file: List[UploadFile] = File(...)):
    """
    Accepts one or more audio files and returns transcriptions.
    Files uploaded are modified to have a unique filename if the name already exists.
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for transcription."
        )

    transcriber = get_transcriber()
    results = []

    for upload_file in file:
        original_filename = upload_file.filename or "audio.mp3"
        try:
            content = await upload_file.read()
            if not content:
                continue

            unique_filename, file_path = save_upload_file(content, original_filename)
            logger.info(f"Saved upload as '{unique_filename}' (original: '{original_filename}'). Transcribing...")

            # Whisper inference is CPU-bound and blocking; run it in a worker thread so it
            # doesn't freeze the single event loop for unrelated concurrent requests
            # (health checks, listings, other uploads) while this file transcribes.
            transcript_text = await asyncio.to_thread(transcriber.transcribe, file_path)

            record = insert_transcription(
                filename=unique_filename,
                original_filename=original_filename,
                transcript=transcript_text
            )
            results.append(record)
        except Exception as e:
            logger.error(f"Error processing file '{original_filename}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process '{original_filename}': {str(e)}"
            )

    return results

@app.get("/transcriptions", summary="Get All Transcriptions")
def list_transcriptions():
    """Retrieves all transcriptions from the SQLite database."""
    return get_all_transcriptions()

@app.get("/search", summary="Search Transcriptions by Filename")
def search(filename: Optional[str] = Query(None, description="Audio file name or substring to search for")):
    """
    Query for transcriptions based on the audio file name (or original filename).
    """
    if not filename or not filename.strip():
        return get_all_transcriptions()
    return search_transcriptions(filename.strip())
