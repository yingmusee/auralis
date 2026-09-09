import os
import uuid
from pathlib import Path
from typing import Tuple
from app.database import filename_exists

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")

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
