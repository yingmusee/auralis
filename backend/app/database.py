import sqlite3
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_PATH = os.environ.get("DATABASE_PATH", "auralis.db")

def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Optional[str] = None):
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    original_filename TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transcriptions_filename ON transcriptions(filename);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transcriptions_orig_name ON transcriptions(original_filename);")
    finally:
        conn.close()

def filename_exists(filename: str, db_path: Optional[str] = None) -> bool:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM transcriptions WHERE filename = ? LIMIT 1", (filename,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

def insert_transcription(filename: str, original_filename: str, transcript: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    created_at = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO transcriptions (filename, original_filename, transcript, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (filename, original_filename, transcript, created_at)
            )
            record_id = cursor.lastrowid
            return {
                "id": record_id,
                "filename": filename,
                "original_filename": original_filename,
                "transcript": transcript,
                "created_at": created_at
            }
    finally:
        conn.close()

def get_all_transcriptions(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, original_filename, transcript, created_at FROM transcriptions ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def search_transcriptions(query: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        pattern = f"%{query}%"
        cursor.execute(
            """
            SELECT id, filename, original_filename, transcript, created_at
            FROM transcriptions
            WHERE filename LIKE ? OR original_filename LIKE ?
            ORDER BY id DESC
            """,
            (pattern, pattern)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
