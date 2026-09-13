import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Configure test environment
test_dir = tempfile.mkdtemp()
test_db_path = os.path.join(test_dir, "test_auralis.db")
test_upload_dir = os.path.join(test_dir, "test_uploads")

os.environ["DATABASE_PATH"] = test_db_path
os.environ["UPLOAD_DIR"] = test_upload_dir
os.environ["MOCK_WHISPER"] = "true"

from app import main
from app.database import init_db

app = main.app

@pytest.fixture(autouse=True)
def setup_and_teardown():
    init_db(test_db_path)
    # main._rate_limit_state is a module-level dict keyed by client host, and
    # TestClient always reports the same host ("testclient") for every request -- so
    # without clearing this between tests, /transcribe calls made by one test would
    # count against every later test's rate-limit budget and could make unrelated
    # tests fail with 429 depending on run order.
    main._rate_limit_state.clear()
    yield

client = TestClient(app)

def test_health_check():
    """Unit Test 1: GET /health returns service status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_transcribe_deduplicates_filename_and_appears_in_transcriptions():
    """
    Unit Test 2: POST /transcribe accepts an audio file and returns its transcription.
    A second upload under the same filename is renamed to stay unique, per the spec's
    "modified to be unique if the file name already exists" requirement. Both uploads
    must then be retrievable via GET /transcriptions.
    """
    fake_audio_content = b"fake-audio-bytes-123"

    response1 = client.post(
        "/transcribe",
        files=[("file", ("recording.mp3", fake_audio_content, "audio/mpeg"))]
    )
    assert response1.status_code == 200
    record1 = response1.json()[0]
    assert record1["filename"] == "recording.mp3"
    assert record1["original_filename"] == "recording.mp3"
    assert "transcript" in record1
    assert "created_at" in record1

    # Second upload with identical filename must be renamed to avoid collision.
    response2 = client.post(
        "/transcribe",
        files=[("file", ("recording.mp3", fake_audio_content, "audio/mpeg"))]
    )
    assert response2.status_code == 200
    record2 = response2.json()[0]
    assert record2["filename"] != record1["filename"]
    assert record2["filename"].startswith("recording_")
    assert record2["filename"].endswith(".mp3")
    assert record2["original_filename"] == "recording.mp3"

    # Both uploads must be retrievable from GET /transcriptions.
    records = client.get("/transcriptions").json()
    filenames = [r["filename"] for r in records]
    assert record1["filename"] in filenames
    assert record2["filename"] in filenames

def test_search_transcriptions_by_filename():
    """Unit Test 3: GET /search returns only transcriptions matching the query."""
    client.post(
        "/transcribe",
        files=[("file", ("interview_alpha.mp3", b"data", "audio/mpeg"))]
    )
    client.post(
        "/transcribe",
        files=[("file", ("lecture_beta.mp3", b"data", "audio/mpeg"))]
    )

    response_alpha = client.get("/search?filename=alpha")
    assert response_alpha.status_code == 200
    results_alpha = response_alpha.json()
    assert any("interview_alpha.mp3" in r["original_filename"] for r in results_alpha)
    assert not any("lecture_beta.mp3" in r["original_filename"] for r in results_alpha)

    response_beta = client.get("/search?filename=beta")
    assert response_beta.status_code == 200
    results_beta = response_beta.json()
    assert any("lecture_beta.mp3" in r["original_filename"] for r in results_beta)
    assert not any("interview_alpha.mp3" in r["original_filename"] for r in results_beta)
