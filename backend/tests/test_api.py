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

import app.main as main
from app.database import init_db, insert_transcription
from app.storage import insert_transcription_with_retry
from app.transcriber import WhisperTranscriber

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


def test_api_root_returns_service_information():
    """GET / returns a useful API entry point rather than a generic 404."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["docs"] == "/docs"

def test_empty_file_upload_is_reported_as_a_per_file_error():
    """
    An empty (0-byte) file used to be silently `continue`d past in main.py -- no error,
    no DB row, and nothing in the response to tell the caller their file was ignored.
    Now that /transcribe returns a per-file status array anyway, this confirms an empty
    file shows up as an explicit "error" entry instead of vanishing without a trace.
    """
    response = client.post(
        "/transcribe",
        files=[("file", ("empty.mp3", b"", "audio/mpeg"))]
    )
    assert response.status_code == 207
    results = response.json()
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert results[0]["filename"] == "empty.mp3"
    assert "empty" in results[0]["detail"]

def test_upload_exceeding_size_limit_is_reported_as_a_per_file_error():
    """
    main.py caps each uploaded file at MAX_UPLOAD_BYTES so the unauthenticated
    /transcribe endpoint can't be trivially used for memory exhaustion (see README's
    "Known Limitations"). Per the batch-partial-failure fix, a single oversized file
    doesn't abort the whole request -- it's reported as one "error" entry (413's detail
    carried through) in an otherwise-207 response, not silently accepted or turned into
    a generic 500.
    """
    oversized_content = b"x" * (main.MAX_UPLOAD_BYTES + 1)
    response = client.post(
        "/transcribe",
        files=[("file", ("too_big.mp3", oversized_content, "audio/mpeg"))]
    )
    assert response.status_code == 207
    results = response.json()
    assert len(results) == 1
    assert results[0]["status"] == "error"
    assert results[0]["filename"] == "too_big.mp3"
    assert "25 MB" in results[0]["detail"]

def test_exceeding_rate_limit_returns_429():
    """
    main.py rate-limits /transcribe per client (RATE_LIMIT_MAX_REQUESTS per
    RATE_LIMIT_WINDOW_SECONDS) since there's no auth in front of it to otherwise limit
    who can trigger CPU-bound Whisper inference. This confirms the limit actually kicks
    in, rather than just existing as unenforced constants.
    """
    for i in range(main.RATE_LIMIT_MAX_REQUESTS):
        response = client.post(
            "/transcribe",
            files=[("file", (f"clip_{i}.mp3", b"data", "audio/mpeg"))]
        )
        assert response.status_code == 200, f"request {i} unexpectedly failed: {response.text}"

    response = client.post(
        "/transcribe",
        files=[("file", ("one_too_many.mp3", b"data", "audio/mpeg"))]
    )
    assert response.status_code == 429

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
    # get_unique_filename() (storage.py) builds the renamed candidate as
    # f"{stem}_{suffix}{ext}" -- checking only startswith("recording_") above wouldn't
    # notice a bug that dropped the extension (e.g. f"{stem}_{suffix}" with no {ext}),
    # since that would still start with "recording_" and pass. This assertion is what
    # actually pins the extension down.
    assert record2["filename"].endswith(".mp3")
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

def test_concurrent_same_filename_upload_does_not_500():
    """
    get_unique_filename() (storage.py) checks disk/DB and then returns a name it
    believes is free, but two concurrent uploads of the same original filename can
    both pass that check before either has actually claimed the name -- a TOCTOU
    race. This simulates that outcome directly against insert_transcription_with_retry
    and asserts it recovers under a fresh filename instead of surfacing
    sqlite3.IntegrityError as an unhandled 500.
    """
    # First request completes normally and claims "race.mp3".
    response1 = client.post(
        "/transcribe",
        files=[("file", ("race.mp3", b"first-upload", "audio/mpeg"))]
    )
    assert response1.status_code == 200

    # Simulate a second concurrent request that, due to the race, also decided
    # "race.mp3" was free and already wrote its own file under that exact name
    # before attempting to insert its record.
    raced_path = os.path.join(test_upload_dir, "race.mp3")
    with open(raced_path, "wb") as f:
        f.write(b"second-upload")

    record = insert_transcription_with_retry("race.mp3", raced_path, "race.mp3", "second transcript")

    assert record["filename"] != "race.mp3"
    assert record["filename"].startswith("race_")
    assert record["filename"].endswith(".mp3")
    assert os.path.exists(os.path.join(test_upload_dir, record["filename"]))

def test_partial_batch_failure_reports_per_file_status():
    """
    A batch upload processes each file independently. main.py's /transcribe used to
    abort the entire request with a single 500 as soon as one file raised, discarding
    the response for files earlier in the same batch that had already been transcribed
    and committed to SQLite -- the caller had no way to know those actually succeeded.
    This asserts the response instead reports each file's real outcome, and that
    earlier successes are both reported AND actually persisted.
    """
    def fake_transcribe(self, audio_path):
        if "bad" in audio_path:
            raise RuntimeError("simulated transcription failure")
        return f"Transcribed text for {os.path.basename(audio_path)}"

    with patch.object(WhisperTranscriber, "transcribe", fake_transcribe):
        response = client.post(
            "/transcribe",
            files=[
                ("file", ("batch_good1.mp3", b"data", "audio/mpeg")),
                ("file", ("batch_bad.mp3", b"data", "audio/mpeg")),
                ("file", ("batch_good2.mp3", b"data", "audio/mpeg")),
            ]
        )

    assert response.status_code == 207
    results = response.json()
    assert len(results) == 3

    assert results[0]["status"] == "ok"
    assert results[0]["original_filename"] == "batch_good1.mp3"

    assert results[1]["status"] == "error"
    assert results[1]["filename"] == "batch_bad.mp3"
    # The detail sent to the client is intentionally generic (see main.py) so the real
    # exception text -- which could contain internal file paths or library internals --
    # is never disclosed to the caller; it must still be findable in server logs.
    assert "simulated transcription failure" not in results[1]["detail"]
    assert "batch_bad.mp3" in results[1]["detail"]

    assert results[2]["status"] == "ok"
    assert results[2]["original_filename"] == "batch_good2.mp3"

    # The two successes must actually be persisted, not just reported as such.
    persisted_names = [r["original_filename"] for r in client.get("/transcriptions").json()]
    assert "batch_good1.mp3" in persisted_names
    assert "batch_good2.mp3" in persisted_names

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

def test_search_matches_via_original_filename_when_stored_filename_differs():
    """
    database.py's search query is `WHERE filename LIKE ? OR original_filename LIKE ?`.
    Every other search test uploads first-time filenames, so filename == original_filename
    for every row -- and get_unique_filename()'s rename scheme (f"{stem}_{suffix}{ext}")
    always keeps the original stem as a prefix anyway, so even a renamed-on-collision row
    still matches on `filename` alone. Neither case can tell OR apart from a mutated AND.
    Inserting directly with a `filename` that shares no substring with `original_filename`
    closes that gap: only the OR clause can match this row by searching the original name.
    """
    insert_transcription(
        filename="a1b2c3d4.mp3",
        original_filename="quarterly_review.mp3",
        transcript="unrelated filename on disk"
    )

    response = client.get("/search?filename=quarterly")
    assert response.status_code == 200
    results = response.json()
    assert any(r["original_filename"] == "quarterly_review.mp3" for r in results)
