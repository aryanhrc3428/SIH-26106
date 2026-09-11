# INSTRUCTIONS.md: Module 2 Agent Build Brief
## API Gateway, Async Orchestration, and Forensic Reporting

---

## 1. Mission

Build the FastAPI gateway for SIH 26106. Module 2 accepts email evidence from Module 1, stages the files, dispatches Celery work to Modules 3, 4, and 5, invokes Module 6 as the final callback, aggregates all findings, and exports PDF/JSON forensic reports.

This module must be fully buildable without any sibling module running. Use `CLAUDE.md` as the source of truth for all interfaces.

---

## 2. Architecture Boundary

* Build inside `Module-2/`.
* Do not create a nested project directory.
* Do not import code from sibling module directories.
* Expose public HTTP only to Module 1.
* Communicate with Modules 3, 4, 5, and 6 only through Celery task names and serialized payloads.
* Do not implement header parsing, GeoIP lookup, NLP inference, graph writes, or database persistence owned by other modules.
* Module 2 may read from persistence stores in integrated mode but must not write to Neo4j, PostgreSQL, or Elasticsearch.

---

## 3. Required Stack

* Python 3.11+
* FastAPI
* Pydantic V2 and Pydantic Settings
* Celery
* Redis
* ReportLab
* PyJWT
* HTTPX
* Pytest

---

## 4. File Layout

Create this layout directly under `Module-2/`:

```text
app/
  main.py
  core/config.py
  core/security.py
  core/celery_app.py
  core/redis.py
  api/v1/router.py
  api/v1/endpoints/ingest.py
  api/v1/endpoints/cases.py
  api/v1/endpoints/graph.py
  api/v1/endpoints/reports.py
  schemas/frontend_contracts.py
  schemas/engine_payloads.py
  schemas/requests.py
  tasks/pipeline.py
  tasks/pdf_generator.py
  services/aggregator.py
  services/storage.py
  services/mock_results.py
  utils/crypto.py
  utils/formatters.py
contracts/
  module3-header-result.sample.json
  module4-geoip-result.sample.json
  module5-nlp-result.sample.json
  module6-graph-result.sample.json
  analysis-result.sample.json
tests/
  test_ingest_api.py
  test_orchestrator.py
  test_aggregator.py
  test_pdf_generator.py
requirements.txt
Dockerfile
```

---

## 5. Input and Output Mapping

### Inputs Consumed

| Source | Transport | Data | Local owner |
| --- | --- | --- | --- |
| Module 1 | HTTP multipart | `.eml` or `.msg`, `client_timestamp`, `analyst_id`, optional `client_sha256` | `api/v1/endpoints/ingest.py` |
| Module 3 | Celery result | Header/authentication payload | `schemas/engine_payloads.py` |
| Module 4 | Celery result | Hop, GeoIP, ASN, domain intel payload | `schemas/engine_payloads.py` |
| Module 5 | Celery result | Content classification and URL payload | `schemas/engine_payloads.py` |
| Module 6 | Celery callback result | Composite score, campaign, persistence payload, `graph_projection` | `schemas/engine_payloads.py` |

### Outputs Produced

| Destination | Transport | Data | Required behavior |
| --- | --- | --- | --- |
| Module 1 | `202 POST /api/v1/cases/upload` | `UploadAccepted` | Return after staging and dispatching work |
| Module 1 | `GET /api/v1/cases/{case_id}/analysis` | `AnalysisResult` | Stable shape for pending, complete, degraded, and failed cases |
| Module 1 | `GET /api/v1/cases/{case_id}/graph` | `NetworkGraphData` | Fixture-backed in standalone mode, read-only graph query in integration |
| Module 1 | `GET /api/v1/reports/{case_id}/export` | PDF blob or JSON | Include chain-of-custody metadata |
| Modules 3, 4, 5 | Celery chord tasks | `case_id`, staged `file_path` | Dispatch in parallel |
| Module 6 | Celery callback | `results`, `case_id` | Run after Modules 3, 4, and 5 complete |

---

## 6. Implementation Requirements

1. Define Pydantic models for all Module 1 request/response contracts and all worker result contracts.
2. Reject unsupported uploads before task dispatch.
3. Calculate and store SHA-256 for each staged file before dispatch.
4. Use Celery `chord` for parallel execution of Modules 3, 4, and 5, with Module 6 as callback.
5. Configure task routing by task name and queue name, not by importing worker code.
6. Add `CELERY_TASK_ALWAYS_EAGER=true` support for tests.
7. Implement aggregation that creates defaults for missing, failed, or invalid worker outputs.
8. Cache the latest Module 6 `graph_projection` so the graph endpoint can work without knowing Neo4j internals.
9. Generate PDF reports from the same validated analysis data returned to Module 1.
10. Sanitize every public error response.

---

## 7. Required Celery Names

```python
tasks.module3_header_analysis
tasks.module4_geoip_analysis
tasks.module5_nlp_analysis
tasks.module6_graph_correlation_and_persist
```

Queue names:

```text
queue_header_forensics
queue_geoip_intel
queue_nlp_fraud
queue_graph_attribution
```

---

## 8. Testing Requirements

Write tests for:

* Upload validation for extension, size, and malformed multipart input
* SHA-256 calculation
* Celery chord construction using task names
* Aggregator behavior when all workers succeed
* Aggregator behavior when one worker returns `FAILED`
* Aggregator behavior when a worker returns invalid JSON
* Graph endpoint response from cached Module 6 `graph_projection`
* PDF generation with case id, file name, hash, timestamp, risk score, and hop table
* Public response sanitization

---

## 9. Environment Variables

```bash
SERVER_HOST="0.0.0.0"
SERVER_PORT="8000"
SECRET_KEY="dev_only_change_me"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES="480"
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/1"
CELERY_TASK_ALWAYS_EAGER="false"
EVIDENCE_STAGING_DIR="/tmp/sih_evidence_staging"
PDF_OUTPUT_DIR="/tmp/sih_pdf_reports"
MAX_UPLOAD_SIZE_BYTES="26214400"
```

Do not commit production secrets.

---

## 10. Independent Compile Gate

Run these commands from `Module-2/` before handing off:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
pytest tests/ -v --cov=app
python -c "from app.main import app; print(app.title)"
```

The test suite must pass with mocked worker payloads and no sibling modules running.
