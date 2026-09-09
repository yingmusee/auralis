# Auralis — Audio Transcription & Search Platform

A full-stack speech-to-text application built with **FastAPI**, **React (Vite)**, **Hugging Face Whisper (`openai/whisper-tiny`)**, and **SQLite**.

---

## 🌟 Features

- **Audio Transcription Pipeline**: Ingests single or batch audio files (MP3, WAV, M4A, etc.), resamples audio to 16 kHz mono float32, and runs in-process speech-to-text inference with `openai/whisper-tiny`.
- **Drag-and-Drop Upload**: HTML5 Drag & Drop onto the upload panel (with a standard file picker fallback) and a real upload-progress bar driven by `XMLHttpRequest`'s `upload.onprogress`.
- **Deduplication Engine**: Automatically checks for filename collisions in both disk storage and SQLite, renaming colliding files to `{stem}_{uuid[:8]}{ext}` while preserving original filenames.
- **Search Functionality**: Server-backed substring search querying SQLite indexes across stored and original audio filenames.
- **Containerized Architecture**: Production-ready `Dockerfile` configurations for both frontend and backend orchestrated seamlessly with Docker Compose.
- **Comprehensive Testing**: Automated unit tests for both backend (`pytest`) and frontend (`vitest` + React Testing Library).
- **Architecture Documentation**: Vector-rendered [architecture.pdf](architecture.pdf) detailing system components, assumptions, scalability matrix, and design considerations.

---

## 🏗️ Architecture Overview

```
                        +-----------------------------------------+
                        |           Docker Compose Network        |
                        |                                         |
[ Browser / Client ] --(Port 3000)--> [ Frontend (Nginx/React) ]  |
                                                |                 |
                                        HTTP REST (JSON/Files)    |
                                                v                 |
                                      [ Backend (FastAPI) ]       |
                                         (Port 8000)              |
                                        /           \             |
                         SQL Queries   /             \ In-Process |
                                      v               v           |
                             [ SQLite DB ]    [ Whisper-Tiny ]    |
                             (auralis.db)      (Hugging Face)     |
                        +-----------------------------------------+
```

See [architecture.pdf](architecture.pdf) for the complete diagram, component breakdown, and design trade-offs.

---

## 🚀 Quick Start with Docker Compose

Ensure Docker and Docker Compose are installed and running:

```bash
# Build and start all services in detached mode
docker compose up --build

# View container logs
docker compose logs -f
```

- **Frontend Application**: [http://localhost:3000](http://localhost:3000)
- **Backend API & Health**: [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive OpenAPI/Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

The backend accepts browser requests from `http://localhost:3000` in Docker Compose
and `http://localhost:5173` during local Vite development. Set `ALLOWED_ORIGINS` to a
comma-separated list of origins when deploying elsewhere.

The Whisper model is downloaded and warmed up during backend startup (before `/health`
reports ready), so the first `docker compose up` can take a minute or two while it
pulls the ~151 MB `openai/whisper-tiny` weights. The download is cached in the
`backend-hf-cache` Docker volume, so subsequent restarts and rebuilds start up quickly
without re-downloading.

To stop services:
```bash
docker compose down
```

---

## 🛠️ Local Development Setup

### Automated Setup (Entire Project)

You can run the automated setup script directly from the repository root:

```bash
chmod +x setup.sh
./setup.sh
```
This automatically sets up the Python virtual environment in `backend/`, installs all backend requirements, and installs frontend npm dependencies.

---

### 1. Backend Setup (Python 3.11+)

You can also set up the backend individually:

```bash
cd backend

# Option A: Run backend setup script
chmod +x setup.sh
./setup.sh

# Option B: Manual virtual environment setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Running Backend Locally:
```bash
# From the backend/ directory with venv activated:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup (Node.js 18+)

```bash
cd frontend

# Install dependencies
npm install

# Start local Vite development server (runs on http://localhost:5173)
npm run dev
```

---

## 🧪 Running Unit Tests

### Backend Unit Tests (Pytest)

The backend includes 5 unit tests in [`backend/tests/test_api.py`](backend/tests/test_api.py) verifying the service information and health endpoints, audio ingestion, filename deduplication on collision, transcription retrieval, and filename search queries.

```bash
cd backend
source venv/bin/activate
pytest -v
```

### Frontend Unit Tests (Vitest)

The frontend includes 4 unit tests in [`frontend/src/App.test.jsx`](frontend/src/App.test.jsx) verifying transcription table rendering, file upload with progress reporting, drag-and-drop file selection, and search interactions.

```bash
cd frontend
npm test
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Returns service health status (`{"status": "ok"}`). |
| `POST` | `/transcribe` | Ingests `multipart/form-data` with key `file` (single or multiple). Deduplicates colliding filenames, pre-processes audio, transcribes with Whisper, and persists record in SQLite. |
| `GET` | `/transcriptions` | Retrieves all transcription records ordered chronologically (newest first). |
| `GET` | `/search?filename=<query>` | Substring search against audio filenames. |

### Sample Transcription Response:
```json
[
  {
    "id": 1,
    "filename": "Sample 1.mp3",
    "original_filename": "Sample 1.mp3",
    "transcript": "Transcribed speech output text.",
    "created_at": "2026-09-09T08:16:00.123456+00:00"
  }
]
```

---

## 📁 Repository Structure

```
.
├── architecture.pdf              # Full architectural diagram & design report
├── docker-compose.yml            # Multi-container orchestration
├── setup.sh                      # Root automated environment setup script
├── README.md                     # Documentation & setup instructions
├── samples/                      # Provided sample audio files (Sample 1, 2, 3)
│   ├── Sample 1.mp3
│   ├── Sample 2.mp3
│   └── Sample 3.mp3
├── backend/                      # Backend service (Python / FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── setup.sh
│   ├── app/
│   │   ├── main.py               # FastAPI endpoints & CORS
│   │   ├── database.py           # SQLite connection & queries
│   │   ├── storage.py            # Unique filename deduplication & file saving
│   │   └── transcriber.py        # Audio preprocessing & Whisper pipeline
│   ├── tests/
│   │   └── test_api.py           # 5 backend unit tests
│   └── uploads/                  # Uploaded audio files storage
└── frontend/                     # Frontend service (React / Vite)
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx               # Upload, table, and search UI
        ├── App.test.jsx          # 4 frontend unit tests
        ├── api.js                # API client helper
        └── styles.css
```
