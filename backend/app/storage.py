import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from app.database import filename_exists, insert_transcription

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
MAX_DEDUP_RETRIES = 5

def ensure_upload_dir(upload_dir: str = UPLOAD_DIR) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

def save_upload_file(file_bytes: bytes, original_filename: str, upload_dir: str = UPLOAD_DIR) -> tuple[str, str]:
    """
    Saves file bytes to disk with a unique filename.
    Returns (unique_filename, file_path_on_disk).
    """
    ensure_upload_dir(upload_dir)
    safe_name = Path(original_filename).name
    path = Path(safe_name)
    stem, suffix = path.stem, path.suffix
    candidate = safe_name

    while True:
        if filename_exists(candidate):
            candidate = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
            continue

        dest_path = os.path.join(upload_dir, candidate)
        try:
            # Reserve the path atomically so concurrent uploads cannot overwrite
            # one another between the collision check and the write.
            fd = os.open(dest_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            candidate = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
            continue

        try:
            with os.fdopen(fd, "wb") as file_handle:
                file_handle.write(file_bytes)
        except Exception:
            try:
                os.unlink(dest_path)
            except FileNotFoundError:
                pass
            raise
        return candidate, dest_path

def insert_transcription_with_retry(
    unique_filename: str, file_path: str, original_filename: str, transcript: str
) -> dict[str, Any]:
    """
    Inserts the transcription record, retrying under a fresh filename if `unique_filename`
    turns out to already be taken.

    The upload path is reserved atomically before the file is written, while SQLite's
    UNIQUE constraint remains the final safeguard if another process claims the same
    database name first.
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
                try:
                    os.unlink(file_path)
                except FileNotFoundError:
                    pass
                raise
            stem, suffix = Path(unique_filename).stem, Path(unique_filename).suffix
            unique_filename = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
            new_path = os.path.join(os.path.dirname(file_path), unique_filename)
            os.rename(file_path, new_path)
            file_path = new_path
