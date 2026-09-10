import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple
from app.database import filename_exists, insert_transcription

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
MAX_DEDUP_RETRIES = 5

def ensure_upload_dir(upload_dir: str = UPLOAD_DIR) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

def get_unique_filename(original_filename: str, upload_dir: str = UPLOAD_DIR) -> str:
    """
    If the filename already exists in the backend (on disk or in the database),
    modifies it to be unique by appending a short uuid hex to the stem.
    """
    ensure_upload_dir(upload_dir)
    safe_name = Path(original_filename).name
    path = Path(safe_name)
    stem = path.stem
    suffix = path.suffix

    candidate = safe_name
    file_path = os.path.join(upload_dir, candidate)

    # Check both database and disk
    while filename_exists(candidate) or os.path.exists(file_path):
        unique_suffix = uuid.uuid4().hex[:8]
        candidate = f"{stem}_{unique_suffix}{suffix}"
        file_path = os.path.join(upload_dir, candidate)

    return candidate

def save_upload_file(file_bytes: bytes, original_filename: str, upload_dir: str = UPLOAD_DIR) -> Tuple[str, str]:
    """
    Saves file bytes to disk with a unique filename.
    Returns (unique_filename, file_path_on_disk).
    """
    ensure_upload_dir(upload_dir)
    unique_name = get_unique_filename(original_filename, upload_dir)
    dest_path = os.path.join(upload_dir, unique_name)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    return unique_name, dest_path

def insert_transcription_with_retry(
    unique_filename: str, file_path: str, original_filename: str, transcript: str
) -> Dict[str, Any]:
    """
    Inserts the transcription record, retrying under a fresh filename if `unique_filename`
    turns out to already be taken.

    get_unique_filename() checks disk/DB and then returns a name it believes is free, but
    that check and this insert aren't atomic (a TOCTOU race): two requests uploading the
    same original filename can both pass the check before either has actually claimed the
    name. So this insert's UNIQUE constraint on `filename` — not the earlier check — is
    the real guarantee. On a collision, rename the already-saved file to a fresh unique
    name and retry, instead of letting sqlite3.IntegrityError surface as an unhandled 500.
    """
    for attempt in range(MAX_DEDUP_RETRIES):
        try:
            return insert_transcription(
                filename=unique_filename,
                original_filename=original_filename,
                transcript=transcript
            )
        except sqlite3.IntegrityError:
            if attempt == MAX_DEDUP_RETRIES - 1:
                raise
            stem, suffix = Path(unique_filename).stem, Path(unique_filename).suffix
            unique_filename = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
            new_path = os.path.join(os.path.dirname(file_path), unique_filename)
            os.rename(file_path, new_path)
            file_path = new_path
