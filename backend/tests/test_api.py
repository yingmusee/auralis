import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Configure test environment
test_dir = tempfile.mkdtemp()
test_db_path = os.path.join(test_dir, "test_auralis.db")
test_upload_dir = os.path.join(test_dir, "test_uploads")

os.environ["DATABASE_PATH"] = test_db_path
os.environ["UPLOAD_DIR"] = test_upload_dir
os.environ["MOCK_WHISPER"] = "true"

from app.main import app
from app.database import init_db

@pytest.fixture(autouse=True)
def setup_and_teardown():
    init_db(test_db_path)
    yield

client = TestClient(app)

def test_health_check():
    """Unit Test 1: GET /health returns service status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_root_returns_service_information():
    """GET / returns a useful API entry point rather than a generic 404."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["docs"] == "/docs"

def test_transcribe_and_filename_deduplication():
    """
    Unit Test 2: POST /transcribe accepts audio files, returns transcription,
    and deduplicates filename when identical filename already exists in the backend.
    """
    fake_audio_content = b"fake-audio-bytes-123"

    # First upload: "recording.mp3"
    response1 = client.post(
        "/transcribe",
        files=[("file", ("recording.mp3", fake_audio_content, "audio/mpeg"))]
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert isinstance(data1, list)
    assert len(data1) == 1
    record1 = data1[0]
    assert record1["filename"] == "recording.mp3"
    assert record1["original_filename"] == "recording.mp3"
    assert "transcript" in record1
    assert "created_at" in record1

    # Second upload with identical filename: should be renamed to avoid collision
    response2 = client.post(
        "/transcribe",
        files=[("file", ("recording.mp3", fake_audio_content, "audio/mpeg"))]
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2) == 1
    record2 = data2[0]
    # Filename must be modified to be unique
    assert record2["filename"] != record1["filename"]
    assert record2["filename"].startswith("recording_")
    assert record2["original_filename"] == "recording.mp3"

def test_get_transcriptions():
    """Unit Test 3: GET /transcriptions retrieves all stored records from database."""
    # Ensure there is data
    client.post(
        "/transcribe",
        files=[("file", ("meeting_notes.mp3", b"audio-data", "audio/mpeg"))]
    )

    response = client.get("/transcriptions")
    assert response.status_code == 200
    records = response.json()
    assert isinstance(records, list)
    assert len(records) >= 1
    filenames = [r["original_filename"] for r in records]
    assert "meeting_notes.mp3" in filenames

def test_search_transcriptions_by_filename():
    """Unit Test 4: GET /search returns transcriptions matching the query."""
    # Upload distinct files
    client.post(
        "/transcribe",
        files=[("file", ("interview_alpha.mp3", b"data", "audio/mpeg"))]
    )
    client.post(
        "/transcribe",
        files=[("file", ("lecture_beta.mp3", b"data", "audio/mpeg"))]
    )

    # Search for "alpha"
    response_alpha = client.get("/search?filename=alpha")
    assert response_alpha.status_code == 200
    results_alpha = response_alpha.json()
    assert any("interview_alpha.mp3" in r["original_filename"] for r in results_alpha)
    assert not any("lecture_beta.mp3" in r["original_filename"] for r in results_alpha)

    # Search for "beta"
    response_beta = client.get("/search?filename=beta")
    assert response_beta.status_code == 200
    results_beta = response_beta.json()
    assert any("lecture_beta.mp3" in r["original_filename"] for r in results_beta)
    assert not any("interview_alpha.mp3" in r["original_filename"] for r in results_beta)
