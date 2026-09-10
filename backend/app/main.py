import asyncio
import os
import logging
from collections import deque
from time import monotonic
from typing import Deque, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile, File, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db, get_all_transcriptions, search_transcriptions
from app.storage import save_upload_file, insert_transcription_with_retry, ensure_upload_dir
from app.transcriber import get_transcriber

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("auralis.api")

# There's no authentication in front of this API (see README's "Known Limitations"),
# so these two limits are what keep an open /transcribe endpoint from being a trivial
# memory- or CPU-exhaustion target.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
UPLOAD_READ_CHUNK_BYTES = 1024 * 1024
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60

_rate_limit_state: Dict[str, Deque[float]] = {}

async def _read_upload_within_limit(upload_file: UploadFile, max_bytes: int) -> bytes:
    """Reads an upload in chunks, aborting before buffering more than max_bytes in memory."""
    chunks = []
    total = 0
    while True:
        chunk = await upload_file.read(UPLOAD_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File '{upload_file.filename}' exceeds the {max_bytes // (1024 * 1024)} MB upload limit."
            )
        chunks.append(chunk)
    return b"".join(chunks)

def _enforce_rate_limit(client_key: str) -> None:
    """Rejects a request if client_key has made too many requests within the window."""
    now = monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps = _rate_limit_state.setdefault(client_key, deque())
    while timestamps and timestamps[0] < window_start:
        timestamps.popleft()
    if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many transcription requests. Please wait before retrying."
        )
    timestamps.append(now)

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
async def transcribe(request: Request, file: List[UploadFile] = File(...)):
    """
    Accepts one or more audio files and transcribes each independently.

    Each file's outcome is reported as its own entry in the response (`status: "ok"`
    or `status: "error"`) rather than one file's failure aborting the whole request.
    Earlier files in the same batch are already saved and committed to SQLite by the
    time a later file fails, so discarding the response in favor of a single error
    would hide those successes from the caller without undoing them -- returning
    per-file status keeps the response honest about what's actually in the database.
    Responds 200 if every file succeeded, 207 (Multi-Status) if any did not.
    """
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for transcription."
        )

    client_key = request.client.host if request.client else "unknown"
    _enforce_rate_limit(client_key)

    transcriber = get_transcriber()
    results = []
    any_errors = False

    for upload_file in file:
        original_filename = upload_file.filename or "audio.mp3"
        try:
            content = await _read_upload_within_limit(upload_file, MAX_UPLOAD_BYTES)
            if not content:
                # Previously just skipped with no signal at all -- the caller had no way
                # to tell "this file was empty and ignored" apart from "everything in the
                # batch succeeded". Now that the response is a per-file status array
                # anyway (see the batch-partial-failure fix above), reporting it costs
                # nothing extra.
                any_errors = True
                results.append({
                    "status": "error",
                    "filename": original_filename,
                    "detail": f"'{original_filename}' is empty and was not transcribed."
                })
                continue

            unique_filename, file_path = save_upload_file(content, original_filename)
            logger.info(f"Saved upload as '{unique_filename}' (original: '{original_filename}'). Transcribing...")

            # Whisper inference is CPU-bound and blocking; run it in a worker thread so it
            # doesn't freeze the single event loop for unrelated concurrent requests
            # (health checks, listings, other uploads) while this file transcribes.
            transcript_text = await asyncio.to_thread(transcriber.transcribe, file_path)

            record = insert_transcription_with_retry(
                unique_filename, file_path, original_filename, transcript_text
            )
            results.append({"status": "ok", **record})
        except HTTPException as e:
            logger.warning(f"Rejected file '{original_filename}': {e.detail}")
            any_errors = True
            results.append({"status": "error", "filename": original_filename, "detail": str(e.detail)})
        except Exception as e:
            # The real exception (potentially containing internal file paths or library
            # internals from soundfile/librosa/transformers) is logged server-side only;
            # the client gets a generic message so those internals are never disclosed.
            logger.error(f"Error processing file '{original_filename}': {e}", exc_info=True)
            any_errors = True
            results.append({
                "status": "error",
                "filename": original_filename,
                "detail": f"Failed to process '{original_filename}'. See server logs for details."
            })

    status_code = status.HTTP_207_MULTI_STATUS if any_errors else status.HTTP_200_OK
    return JSONResponse(content=results, status_code=status_code)

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
