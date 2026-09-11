# CLAUDE.md: Module 2 Interface Contract
## Module 2: API Gateway, Async Orchestration, and Forensic Reporting

---

## 1. Contract Purpose

This file is the memory contract for the agent building Module 2. Keep only information required to build the gateway independently and integrate with the other modules later.

* **Module ID:** `MOD-02`
* **Build root:** `Module-2/` (create app files directly here; do not create a nested `module-2-mediator/` directory)
* **Primary role:** FastAPI gateway, upload handler, evidence staging service, Celery orchestrator, result aggregator, graph proxy, and PDF/JSON report exporter
* **Consumes from:** Module 1 HTTP requests and Modules 3, 4, 5, and 6 Celery results
* **Produces to:** Module 1 HTTP responses and Celery tasks for Modules 3, 4, 5, and 6
* **Never does:** Frontend rendering, forensic engine internals, NLP inference, GeoIP lookup, direct writes to Neo4j/PostgreSQL/Elasticsearch

Before coding, read `../Architecture_and_Plan.md` and `INSTRUCTIONS.md`.

---

## 2. Required Independence

Module 2 must compile, run, and pass tests without Modules 1, 3, 4, 5, or 6 running.

* Use local contract fixtures or eager Celery test tasks for standalone mode.
* Validate every worker result with Pydantic before aggregation.
* Generate fallback structures when a worker result is missing, invalid, timed out, or marked `FAILED`.
* Keep public API schemas stable for Module 1 even when downstream engines degrade.
* Store staged evidence under `EVIDENCE_STAGING_DIR`; do not require a database for unit tests.

---

## 3. Input Mapping: Data Consumed by Module 2

### 3.1 Upload Request from Module 1

**Endpoint:** `POST /api/v1/cases/upload`

* **Content-Type:** `multipart/form-data`
* **Fields:**
  * `files`: array of `.eml` or `.msg` files
  * `client_timestamp`: ISO 8601 timestamp
  * `analyst_id`: string
  * `client_sha256`: optional SHA-256 hash per file

### 3.2 Worker Result from Module 3

**Celery task consumed:** `tasks.module3_header_analysis`

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "subject": "Urgent Wire Transfer Request",
  "timestamp": "2026-09-06T12:00:00Z",
  "hashes": {
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "md5": "d41d8cd98f00b204e9800998ecf8427e"
  },
  "attachment_hashes": [
    {
      "name": "invoice.pdf",
      "sha256": "a3582418e00192e15347ad915d4acf14aa0741e1438d55ab3e59d6cf00d14d00"
    }
  ],
  "header_anomaly_score": 85.0,
  "spf": {"status": "FAIL", "domain": "spoofed-bank.com", "ip": "192.0.2.1"},
  "dkim": {"status": "FAIL", "selector": "s1", "domain": "spoofed-bank.com"},
  "dmarc": {"status": "FAIL", "policy": "reject", "alignment": false},
  "sender_alignment": {
    "header_from": "billing@legitbank.com",
    "envelope_from": "spammer@evil-server.net",
    "reply_to": "attacker@harvest-site.org",
    "is_display_name_spoofed": true,
    "spoofed_entity_detected": "Legitimate Bank Executive"
  },
  "raw_hop_chain": ["192.0.2.1", "198.51.100.25", "203.0.113.195"],
  "raw_headers": "Received: from relay01.evil-server.net...\nFrom: CEO <billing@legitbank.com>..."
}
```

### 3.3 Worker Result from Module 4

**Celery task consumed:** `tasks.module4_geoip_analysis`

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "geo_risk_score": 90.0,
  "earliest_reliable_ip": "192.0.2.1",
  "origin_country": "RU",
  "origin_city": "Moscow",
  "hops": [
    {
      "hop_index": 1,
      "ip": "192.0.2.1",
      "hostname": "relay01.evil-server.net",
      "country": "RU",
      "city": "Moscow",
      "latitude": 55.7558,
      "longitude": 37.6173,
      "isp": "BadActor Networks LLC",
      "asn": "AS65534",
      "is_vpn_or_proxy": true,
      "is_tor_exit_node": false,
      "delay_from_prev_ms": 0
    }
  ],
  "domain_intel": {
    "domain": "evil-server.net",
    "domain_age_days": 12,
    "registrar": "NameCheap Inc.",
    "is_newly_registered": true,
    "is_typosquatted": true,
    "target_brand_spoofed": "microsoft.com"
  }
}
```

### 3.4 Worker Result from Module 5

**Celery task consumed:** `tasks.module5_nlp_analysis`

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "content_suspicion_score": 92.0,
  "classification": "BEC_FINANCIAL",
  "confidence": 0.96,
  "detected_language": "en",
  "urgency_score": 88.5,
  "text_summary": "Urgent request for wire transfer diversion to updated vendor account.",
  "extracted_urls": [
    {
      "original_url": "http://bit.ly/3x89aQ",
      "final_redirect_url": "https://credential-harvest-login.com/auth",
      "domain_age_days": null,
      "is_suspicious_tld": true,
      "risk_score": 95.0
    }
  ]
}
```

### 3.5 Worker Result from Module 6

**Celery callback consumed:** `tasks.module6_graph_correlation_and_persist`

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "composite_score": 88.75,
  "threat_level": "CRITICAL",
  "graph_reputation_score": 88.0,
  "linked_campaign": {
    "campaign_id": "cmp_991823",
    "campaign_name": "Operation Fake Invoice Alpha",
    "total_linked_emails": 42,
    "first_seen": "2026-08-15T10:00:00Z",
    "last_seen": "2026-09-06T18:00:00Z"
  },
  "nodes_created": 12,
  "relationships_created": 15,
  "graph_projection": {
    "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
    "nodes": [
      {
        "id": "email_case_550e8400",
        "label": "Urgent Wire Transfer Request",
        "type": "EMAIL",
        "properties": {
          "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "threat_level": "CRITICAL"
        },
        "risk_score": 88.75
      }
    ],
    "edges": [],
    "campaign_summary": {
      "campaign_id": "cmp_991823",
      "campaign_name": "Operation Fake Invoice Alpha",
      "total_linked_emails": 42,
      "first_seen": "2026-08-15T10:00:00Z",
      "last_seen": "2026-09-06T18:00:00Z"
    }
  },
  "persistence_status": {
    "postgres_saved": true,
    "elasticsearch_indexed": true,
    "neo4j_synced": true
  }
}
```

### 3.6 Shared Worker Failure Shape

Any worker may return this shape. Module 2 must still return a valid Module 1 payload.

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILED",
  "error": {
    "code": "MODULE_TIMEOUT",
    "message": "Module timed out before completing analysis.",
    "recoverable": true
  }
}
```

---

## 4. Output Mapping: Data Produced by Module 2

### 4.1 Upload Accepted Response to Module 1

```json
{
  "batch_id": "batch_9823b12a-4f51",
  "cases": [
    {
      "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
      "file_name": "suspicious_invoice.eml",
      "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "status": "PROCESSING",
      "estimated_duration_ms": 3000
    }
  ]
}
```

### 4.2 Aggregated Analysis Response to Module 1

**Endpoint:** `GET /api/v1/cases/{case_id}/analysis`

Return the `AnalysisResult` contract defined in `Module-1/CLAUDE.md`.

Field mapping:

| Module 1 field | Source |
| --- | --- |
| `subject`, `timestamp`, `md5_hash`, `sha256_hash`, `raw_headers`, `protocol_forensics` | Module 3 |
| `routing_topology` | Module 4 |
| `content_analysis` | Module 5 |
| `risk_matrix.composite_score`, `threat_level`, `graph_reputation_score`, `linked_campaign` | Module 6 |
| `risk_matrix.flags` | Module 2 aggregation plus degraded worker errors |

### 4.3 Graph Response to Module 1

**Endpoint:** `GET /api/v1/cases/{case_id}/graph`

Return the `NetworkGraphData` contract defined in `Module-1/CLAUDE.md`. Prefer the latest Module 6 `graph_projection` when available. In standalone mode, serve this from contract fixtures. In integrated mode, fall back to read-only graph repositories when the cached projection is absent.

### 4.4 Report Export to Module 1

**Endpoint:** `GET /api/v1/reports/{case_id}/export`

* `format=pdf`: return `application/pdf`
* `format=json`: return `application/json`
* `include_raw_headers=true`: include raw headers in JSON and PDF appendix

### 4.5 Celery Tasks Dispatched to Worker Modules

```python
tasks.module3_header_analysis(case_id: str, file_path: str)
tasks.module4_geoip_analysis(case_id: str, file_path: str, raw_hop_chain: list[str] | None = None)
tasks.module5_nlp_analysis(case_id: str, file_path: str)
tasks.module6_graph_correlation_and_persist(results: list[dict[str, object]], case_id: str)
```

Module 2 dispatches Modules 3, 4, and 5 in parallel. Module 6 runs after those results return.

---

## 5. Failure Handling Contract

* Return `400` for unsupported file types or malformed multipart input.
* Return `413` for files larger than 25 MB.
* Return `422` for request schema validation errors.
* Return `202` for accepted uploads even while engines are still processing.
* Return valid `AnalysisResult` with status `DEGRADED` when one or more engines fail but aggregation can continue.
* Return `FAILED` only when there is no usable staged evidence or no engine result can be trusted.
* Mask stack traces, secrets, local paths, and raw dependency errors in public responses.

---

## 6. Standalone Completion Gate

Module 2 is ready only when these pass from inside `Module-2/`:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
pytest tests/ -v --cov=app
python -c "from app.main import app; print(app.title)"
```

The test suite must pass with mocked worker results and no sibling modules running.
