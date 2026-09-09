import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

def create_architecture_diagram():
    # Width: 550, Height: 210
    d = Drawing(550, 210)
    
    # Background Canvas
    d.add(Rect(0, 0, 550, 210, fillColor=colors.HexColor("#F8FAFC"), strokeColor=colors.HexColor("#E2E8F0"), strokeWidth=1, rx=8, ry=8))
    
    # Docker Network Boundary Box
    d.add(Rect(8, 8, 534, 194, fillColor=None, strokeColor=colors.HexColor("#94A3B8"), strokeWidth=1, strokeDashArray=[4, 4], rx=6, ry=6))
    d.add(String(18, 190, "Docker Compose Project Network (default)", fontSize=8.5, fillColor=colors.HexColor("#64748B"), fontName="Helvetica-Bold"))
    
    # Component A: Frontend Container
    d.add(Rect(20, 30, 130, 150, fillColor=colors.HexColor("#EFF6FF"), strokeColor=colors.HexColor("#3B82F6"), strokeWidth=1.5, rx=5, ry=5))
    d.add(Rect(20, 152, 130, 28, fillColor=colors.HexColor("#3B82F6"), strokeColor=None, rx=5, ry=5))
    d.add(String(34, 161, "Frontend (SPA)", fontSize=10.5, fillColor=colors.white, fontName="Helvetica-Bold"))
    d.add(String(28, 134, "• React 18 + Vite", fontSize=8, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(28, 118, "• Nginx Alpine Server", fontSize=8, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(28, 102, "• Single / Batch Upload", fontSize=8, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(28, 86, "• Live Filename Search", fontSize=8, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(28, 70, "• Port 3000 / 80", fontSize=8, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica-Bold"))
    d.add(String(28, 48, "[Container: frontend]", fontSize=7, fillColor=colors.HexColor("#64748B"), fontName="Helvetica-Oblique"))

    # Arrow 1: Frontend -> Backend (REST / JSON)
    d.add(Line(150, 110, 190, 110, strokeColor=colors.HexColor("#0284C7"), strokeWidth=2))
    d.add(Polygon([190, 113, 197, 110, 190, 107], fillColor=colors.HexColor("#0284C7"), strokeColor=None))
    d.add(String(154, 116, "HTTP REST", fontSize=7, fillColor=colors.HexColor("#0369A1"), fontName="Helvetica-Bold"))
    d.add(String(154, 98, "JSON/Files", fontSize=6.5, fillColor=colors.HexColor("#64748B"), fontName="Helvetica"))

    # Component B: Backend Container
    d.add(Rect(200, 20, 170, 165, fillColor=colors.HexColor("#F0FDF4"), strokeColor=colors.HexColor("#22C55E"), strokeWidth=1.5, rx=5, ry=5))
    d.add(Rect(200, 157, 170, 28, fillColor=colors.HexColor("#16A34A"), strokeColor=None, rx=5, ry=5))
    d.add(String(222, 166, "Backend (FastAPI)", fontSize=10.5, fillColor=colors.white, fontName="Helvetica-Bold"))
    d.add(String(208, 138, "• FastAPI + Uvicorn (Port 8000)", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica-Bold"))
    d.add(String(208, 124, "• Endpoints: /health, /search", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(216, 112, "/transcribe, /transcriptions", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(208, 98, "• Audio Preprocessing (16kHz)", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(208, 84, "• Filename Deduplication", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(208, 70, "• In-Process Whisper Engine", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(208, 56, "• Volumes: /app/uploads, /app/data & /app/hf-cache", fontSize=6.5, fillColor=colors.HexColor("#475569"), fontName="Helvetica"))
    d.add(String(208, 42, "[Container: backend]", fontSize=7, fillColor=colors.HexColor("#64748B"), fontName="Helvetica-Oblique"))

    # Arrow 2: Backend -> Database (SQLite)
    d.add(Line(370, 130, 400, 130, strokeColor=colors.HexColor("#EA580C"), strokeWidth=1.8))
    d.add(Polygon([400, 133, 407, 130, 400, 127], fillColor=colors.HexColor("#EA580C"), strokeColor=None))
    d.add(String(372, 136, "SQL Query", fontSize=6.5, fillColor=colors.HexColor("#C2410C"), fontName="Helvetica-Bold"))

    # Component C: Database (SQLite)
    d.add(Rect(410, 105, 120, 75, fillColor=colors.HexColor("#FFF7ED"), strokeColor=colors.HexColor("#F97316"), strokeWidth=1.5, rx=5, ry=5))
    d.add(Rect(410, 155, 120, 25, fillColor=colors.HexColor("#EA580C"), strokeColor=None, rx=5, ry=5))
    d.add(String(428, 163, "SQLite Database", fontSize=9.5, fillColor=colors.white, fontName="Helvetica-Bold"))
    d.add(String(418, 140, "• File: auralis.db", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica-Bold"))
    d.add(String(418, 126, "• Table: transcriptions", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(418, 112, "• Indexed filename search", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))

    # Arrow 3: Backend -> External Model
    d.add(Line(370, 55, 400, 55, strokeColor=colors.HexColor("#7C3AED"), strokeWidth=1.8))
    d.add(Polygon([400, 58, 407, 55, 400, 52], fillColor=colors.HexColor("#7C3AED"), strokeColor=None))
    d.add(String(372, 61, "Weights Pull", fontSize=6.5, fillColor=colors.HexColor("#6D28D9"), fontName="Helvetica-Bold"))

    # Component D: External Service / Model
    d.add(Rect(410, 20, 120, 75, fillColor=colors.HexColor("#FAF5FF"), strokeColor=colors.HexColor("#A855F7"), strokeWidth=1.5, rx=5, ry=5))
    d.add(Rect(410, 70, 120, 25, fillColor=colors.HexColor("#7C3AED"), strokeColor=None, rx=5, ry=5))
    d.add(String(420, 78, "External Service", fontSize=9.5, fillColor=colors.white, fontName="Helvetica-Bold"))
    d.add(String(418, 55, "• Hugging Face Hub", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica-Bold"))
    d.add(String(418, 41, "• openai/whisper-tiny", fontSize=7.5, fillColor=colors.HexColor("#1E293B"), fontName="Helvetica"))
    d.add(String(418, 28, "• Pretrained weights", fontSize=7, fillColor=colors.HexColor("#475569"), fontName="Helvetica"))

    return d

def generate_pdf(output_filename="architecture.pdf"):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=30,
        rightMargin=30,
        topMargin=26,
        bottomMargin=26
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=7,
        spaceAfter=4
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#334155"),
        spaceBefore=4,
        spaceAfter=2
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
        spaceAfter=2
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=1.5
    )

    story = []

    # Title & Metadata
    story.append(Paragraph("Auralis — System Architecture & Technical Specifications", title_style))
    story.append(Paragraph("<b>Role:</b> Software Engineer Technical Assessment | <b>Project:</b> Auralis Speech-to-Text Platform | <b>Model:</b> openai/whisper-tiny", subtitle_style))

    # 1. Architecture Diagram
    story.append(Paragraph("1. System Architecture Diagram", h1_style))
    story.append(create_architecture_diagram())
    story.append(Spacer(1, 6))

    # 2. Component Breakdown
    story.append(Paragraph("2. Architectural Components Breakdown", h1_style))
    
    story.append(Paragraph("<b>a) Frontend (Single-Page Application):</b>", h2_style))
    story.append(Paragraph("• <b>Stack & Build:</b> React 18, Vite build system, HTML5 Drag & Drop File API, CSS responsive styling.", bullet_style))
    story.append(Paragraph("• <b>Capabilities:</b> Single & batch audio upload via drag-and-drop or file picker with a real-time upload progress bar, persistent transcription records table, and client-to-server filename search.", bullet_style))
    story.append(Paragraph("• <b>Containerization:</b> Packaged with multi-stage Alpine Nginx serving static assets on port 80 (mapped to host 3000).", bullet_style))

    story.append(Paragraph("<b>b) Backend (RESTful Web Service):</b>", h2_style))
    story.append(Paragraph("• <b>Engine & Framework:</b> FastAPI (Python 3.11) with Uvicorn ASGI, asynchronous request handling, CPU-bound Whisper inference offloaded to a worker thread (<code>asyncio.to_thread</code>) so it doesn't block the event loop, and automatic OpenAPI/Swagger documentation.", bullet_style))
    story.append(Paragraph("• <b>Endpoints:</b> <code>GET /health</code> (liveness probe), <code>POST /transcribe</code> (multipart single/batch ingestion with deduplication), <code>GET /transcriptions</code> (chronological record retrieval), <code>GET /search?filename=...</code> (indexed substring query).", bullet_style))
    story.append(Paragraph("• <b>Audio Preprocessing Pipeline:</b> Decodes uploaded formats (MP3/WAV/M4A), resamples audio to 16,000 Hz, downmixes stereo to mono, and normalizes amplitudes to float32 tensors per Whisper specification.", bullet_style))
    story.append(Paragraph("• <b>Filename Deduplication:</b> Prevents overwriting existing backend records by checking disk and SQLite; appends unique deterministic UUID suffix (<code>{stem}_{uuid[:8]}{ext}</code>) while preserving the original user-facing filename.", bullet_style))

    story.append(Paragraph("<b>c) Database (SQLite):</b>", h2_style))
    story.append(Paragraph("• <b>Storage:</b> SQLite 3 relational database (<code>auralis.db</code>) mounted on persistent Docker volume (<code>backend-data</code>).", bullet_style))
    story.append(Paragraph("• <b>Schema & Indexing:</b> Table <code>transcriptions</code> stores <code>id</code> (PK), <code>filename</code> (UNIQUE), <code>original_filename</code>, <code>transcript</code>, and <code>created_at</code> (ISO 8601 UTC). B-Tree indexes on <code>filename</code> and <code>original_filename</code>.", bullet_style))

    story.append(Paragraph("<b>d) External Services & Model Integration:</b>", h2_style))
    story.append(Paragraph("• <b>Model Hub:</b> Hugging Face Hub (<code>openai/whisper-tiny</code>, ~151 MB weights). The model is pre-warmed during FastAPI's startup lifespan, before the container reports healthy, so the first real transcription request is never the one paying the load cost.", bullet_style))
    story.append(Paragraph("• <b>Runtime Dependency:</b> The Hugging Face cache directory is mounted on a persistent Docker volume (<code>backend-hf-cache</code>), so weights are downloaded from Hugging Face Hub once and reused across container restarts and rebuilds; uploaded audio is always processed locally inside the backend container.", bullet_style))

    story.append(PageBreak())

    # PAGE 2: Assumptions & Considerations
    story.append(Paragraph("3. Assumptions and Design Considerations", h1_style))
    
    story.append(Paragraph("<b>A. Operational & Architectural Assumptions:</b>", h2_style))
    story.append(Paragraph("1. <b>In-Process vs. Microservice Inference:</b> Whisper-tiny is executed directly within the FastAPI backend worker process. Given the compact model footprint (39M parameters, ~151MB RAM), in-process inference eliminates network overhead, simplifies deployment into a single backend container, and adheres strictly to the single-repo specification.", bullet_style))
    story.append(Paragraph("2. <b>Single vs. Batch File Contract:</b> The <code>POST /transcribe</code> endpoint standardizes on returning an array of JSON objects with schema fields: <code>id</code>, <code>filename</code>, <code>original_filename</code>, <code>transcript</code>, and <code>created_at</code>.", bullet_style))
    story.append(Paragraph("3. <b>Persistence & Storage Separation:</b> Audio files uploaded by users are saved in <code>uploads/</code> while metadata and transcriptions reside in SQLite. Both directories are mounted via Docker named volumes to survive container restarts and rebuilds.", bullet_style))
    story.append(Paragraph("4. <b>Threaded, Not Parallel, Inference:</b> Whisper inference is CPU-bound and blocking, so it's offloaded to a worker thread (<code>asyncio.to_thread</code>) per file rather than run inline in the async request handler. This keeps the single event loop free to serve unrelated concurrent requests (health checks, listings, other uploads) while a transcription is in progress. Files within one batch upload are still transcribed one at a time against the shared in-memory model; parallelizing them was deliberately left out of scope, since real speedup would need a bounded worker pool and is capped by the container's available CPU cores, not just code changes.", bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>B. Reliability, Performance & Scalability Considerations:</b>", h2_style))
    
    # Table of Considerations
    data = [
        [Paragraph("<b>Domain</b>", body_style), Paragraph("<b>Current Implementation</b>", body_style), Paragraph("<b>Production Scale Recommendation</b>", body_style)],
        [
            Paragraph("<b>Inference Concurrency</b>", body_style),
            Paragraph("CPU inference per file, offloaded to a worker thread so it doesn't block the event loop for other requests; files within one batch upload still transcribe one at a time.", body_style),
            Paragraph("Offload transcription to an asynchronous Celery / Redis task queue with WebSocket status streaming to prevent HTTP timeouts on long audio files.", body_style)
        ],
        [
            Paragraph("<b>Storage Architecture</b>", body_style),
            Paragraph("Local container filesystem mounted to Docker named volume.", body_style),
            Paragraph("Migrate audio storage to cloud object storage (AWS S3, GCP Cloud Storage) with presigned URLs for direct client uploads.", body_style)
        ],
        [
            Paragraph("<b>Database Scaling</b>", body_style),
            Paragraph("Embedded SQLite with B-Tree indexes for fast local lookups.", body_style),
            Paragraph("Migrate to PostgreSQL or distributed relational database with full-text search (pgvector or Elasticsearch) for transcript content searching.", body_style)
        ],
        [
            Paragraph("<b>Security & Compliance</b>", body_style),
            Paragraph("Path-safe filename handling, UUID collision isolation, and configurable CORS origins.", body_style),
            Paragraph("Add rate limiting (SlowAPI), JWT bearer authentication, audio malware scanning (ClamAV), and HTTPS TLS termination at reverse proxy.", body_style)
        ]
    ]

    table = Table(data, colWidths=[105, 195, 250])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(table)

    story.append(Spacer(1, 10))
    story.append(Paragraph("4. Verification & Testing Matrix", h1_style))
    story.append(Paragraph("• <b>Backend Unit Tests:</b> 5 comprehensive pytest suites in <code>backend/tests/test_api.py</code> verifying <code>/health</code>, the API root info response, <code>/transcriptions</code>, substring search filtering, and unique filename collision generation.", bullet_style))
    story.append(Paragraph("• <b>Frontend Unit Tests:</b> 4 Vitest/RTL tests in <code>frontend/src/App.test.jsx</code> verifying tabular transcription rendering, upload with progress reporting, drag-and-drop file selection, and live search query triggering.", bullet_style))
    story.append(Paragraph("• <b>Sample Audio Evaluation:</b> Evaluated on the three provided sample MP3 files (<code>Sample 1.mp3</code>, <code>Sample 2.mp3</code>, <code>Sample 3.mp3</code>) confirming successful end-to-end ingestion and speech transcription.", bullet_style))

    doc.build(story)
    print(f"Architecture PDF successfully generated at: {output_filename}")

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "architecture.pdf"
    generate_pdf(out_file)
