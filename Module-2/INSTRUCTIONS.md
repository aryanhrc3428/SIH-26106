# INSTRUCTIONS.md: AI Agent Designing & Coding Standards
## Module 2: API Gateway, Async Orchestration & Forensic Reporting

---

## 1. Module Identity & Architectural Boundary
* **Module Name:** `module-2-mediator`
* **Owner:** Member 2 (Mediator / Integration Lead)
* **Framework Stack:** Python 3.11+, FastAPI, Pydantic V2, Celery, Redis (Broker & Result Backend), ReportLab (PDF Generation), PyJWT, HTTPX.
* **Core Function:** Functions as the central API Gateway, Task Orchestrator, and Interface Mediator. It exposes REST API contracts to Module 1 (Frontend), dispatches asynchronous work units to Backend Engine Workers (Modules 3, 4, 5, and 6) via Redis message queues, aggregates engine findings into unified payloads, and compiles court-ready PDF evidence reports.
* **Isolation Guarantee:** Module 2 acts as the **SOLE** network boundary facing Module 1. It encapsulates all backend implementation details. Backend Modules 3, 4, 5, and 6 NEVER expose public HTTP endpoints directly to Module 1.

---

## 2. Directory Structure & Code Layout Guidelines

When generating or modifying code for Module 2, strictly follow this repository layout:

```
module-2-mediator/
├── app/
│   ├── main.py                     # FastAPI app factory, CORS, and middleware setup
│   ├── core/
│   │   ├── config.py               # BaseSettings using Pydantic Settings
│   │   ├── security.py             # JWT authentication & RBAC middleware
│   │   ├── celery_app.py           # Celery instance, queue configs & task routing
│   │   └── redis.py                # Async Redis connection pool manager
│   ├── api/
│   │   ├── v1/
│   │   │   ├── router.py           # Main V1 Router aggregation
│   │   │   ├── endpoints/
│   │   │   │   ├── ingest.py       # EML/MSG upload & SHA-256 hashing pre-flight
│   │   │   │   ├── cases.py        # Case status polling & aggregated report endpoints
│   │   │   │   ├── graph.py        # Proxy endpoint for Graph topology data
│   │   │   │   └── reports.py      # PDF / JSON report export trigger
│   ├── schemas/
│   │   ├── frontend_contracts.py   # Strict response models for Module 1 UI
│   │   ├── engine_payloads.py      # Validation models for Modules 3, 4, 5, and 6
│   │   └── requests.py             # File upload and filtering request schemas
│   ├── tasks/
│   │   ├── pipeline.py             # Celery chord/chain workflow orchestrator
│   │   └── pdf_generator.py        # ReportLab PDF compilation service
│   ├── services/
│   │   ├── aggregator.py           # Combines findings from Mod 3, 4, 5, 6 into Risk Matrix
│   │   └── storage.py              # Stashes raw .eml/.msg evidence temporarily
│   └── utils/
│       ├── crypto.py               # SHA-256 calculation & digital signature helpers
│       └── formatters.py           # Date/time & text sanitization helpers
├── tests/
│   ├── test_ingest_api.py
│   ├── test_orchestrator.py
│   └── test_pdf_generator.py
├── requirements.txt
└── Dockerfile
```

---

## 3. Designing & Coding Standards

### A. FastAPI & Pydantic V2 Usage
1. **Strict Type Annotations:** All functions, endpoint handlers, and service methods MUST be typed with Python 3.11+ syntax (`str | None`, `list[dict[str, Any]]`).
2. **Async Handlers:** Standard API endpoints must be asynchronous (`async def`). Heavy CPU or blocking disk operations (e.g., ReportLab PDF rendering) MUST be offloaded to Celery background workers.
3. **Response Schema Enforcement:** All FastAPI path operations MUST explicitly set `response_model=...` matching the contracts defined in `CLAUDE.md`.

### B. Async Task Orchestration (Celery + Redis)
1. **Task Execution Strategy (Parallel Engine Execution):**
   * Use Celery `chord` primitives: Execute Module 3 (Header), Module 4 (GeoIP), and Module 5 (NLP) in parallel.
   * Upon completion of the parallel phase, pass all 3 results to Module 6 (Graph Attribution & Storage Engine) as a callback task.
   * **Task Workflow Primitive:**
     ```python
     from celery import chord
     from app.core.celery_app import celery_app

     def run_forensic_pipeline(case_id: str, file_path: str):
         # Phase 1: Parallel Engine Analysis (Modules 3, 4, 5)
         parallel_engines = [
             celery_app.signature('tasks.module3_header_analysis', args=[case_id, file_path]),
             celery_app.signature('tasks.module4_geoip_analysis', args=[case_id, file_path]),
             celery_app.signature('tasks.module5_nlp_analysis', args=[case_id, file_path]),
         ]
         # Phase 2: Graph Correlation & Final Aggregation Callback (Module 6)
         # Note: Celery prepends parallel results list to args, so kwargs binding is used for case_id
         callback = celery_app.signature('tasks.module6_graph_correlation_and_persist', kwargs={'case_id': case_id})
         
         # Execute Chord
         chord(parallel_engines)(callback)
     ```

2. **Hard Timeouts:** Every task signature MUST enforce `soft_time_limit=25` and `time_limit=30` seconds to prevent stalled workers from locking the pipeline.

### C. PDF Report Generation Engine (ReportLab)
1. **Forensic Integrity Standards:**
   * Generated PDF documents MUST include an **Evidentiary Header** featuring: Case UUID, File Name, Calculated SHA-256 Hash, Generation Timestamp (UTC), and Digital Signature Fingerprint.
2. **Visual Styling:**
   * Dark/Professional palette: Deep Navy `#0F172A`, Slate Gray `#475569`, Alert Red `#E11D48`, Accent Cyan `#0891B2`.
   * Tables: Multi-hop trace tables with explicit column widths, header background fills, and cell word wrapping.

---

## 4. Error Handling & Fault Tolerance Standards

1. **Partial Engine Failure Resilience (CRITICAL):**
   * If one backend module (e.g., Module 5 NLP engine) throws an exception or times out, the Mediator MUST NOT fail the entire case.
   * The `aggregator.py` service MUST populate default fallback structures for the failed engine, mark the specific sub-status as `DEGRADED`, and attach a critical warning flag in the response payload.

2. **Standardized HTTP Exceptions:**
   * `400 Bad Request`: Non-EML/MSG files or corrupted headers.
   * `413 Payload Too Large`: Files exceeding 25 MB limit.
   * `422 Unprocessable Entity`: Failed Pydantic schema validation.
   * `500 Internal Server Error`: Critical pipeline crashes (masked from raw stack traces in production).

---

## 5. Testing & Verification Requirements

1. **Unit Tests:** Test schema validation, HMAC hash calculations, and PDF generation formatting.
2. **Integration Tests:** Test FastAPI upload endpoints, task dispatch mock calls, and result retrieval endpoints using `httpx.AsyncClient`.
3. **Execution Command:**
   ```bash
   pytest tests/ -v --cov=app
   ```
