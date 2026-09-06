# CLAUDE.md: Synced Memory & Module Isolation Interface Contract
## Module 2: API Gateway, Async Orchestration & Forensic Reporting

---

## 1. Module Overview & Memory Context
* **Module ID:** `MOD-02`
* **Purpose:** Central Gateway, Celery Task Orchestrator, Result Aggregator, PDF Report Engine.
* **Current Version:** `1.0.0-prod`
* **Owner:** Member 2 (Mediator / Integration Lead)
* **Upstream Client Target:** Module 1 (Frontend Web UI)
* **Downstream Engine Targets:** Module 3 (Header), Module 4 (GeoIP), Module 5 (NLP), Module 6 (Graph)

---

## 2. Ingress Interface Schema (Inputs Received by Module 2)

### A. From Upstream Client (Module 1 - Frontend)

#### 1. Endpoint: `POST /api/v1/cases/upload`
* **Content-Type:** `multipart/form-data`
* **Request Payload:**
  ```form-data
  files: File[] (.eml or .msg)
  client_timestamp: ISO 8601 String
  analyst_id: String
  ```
* **Success Response Schema (202 Accepted):**
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

---

### B. From Downstream Engine Workers (Modules 3, 4, 5, and 6)

#### 1. Payload from Module 3 (`tasks.module3_header_analysis` completion):
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

#### 2. Payload from Module 4 (`tasks.module4_geoip_analysis` completion):
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

#### 3. Payload from Module 5 (`tasks.module5_nlp_analysis` completion):
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

#### 4. Payload from Module 6 (`tasks.module6_graph_correlation_and_persist` completion):
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
    "total_linked_emails": 42
  },
  "nodes_created": 12,
  "relationships_created": 15,
  "persistence_status": {
    "postgres_saved": true,
    "elasticsearch_indexed": true,
    "neo4j_synced": true
  }
}
```

---

## 3. Egress Interface Schema (Outputs Provided by Module 2)

### A. To Upstream Client (Module 1 - Frontend)

#### 1. Endpoint: `GET /api/v1/cases/{case_id}/analysis`
Aggregates outputs from Modules 3, 4, 5, and 6 into the unified `AnalysisResult` JSON format matching Module 1's `CLAUDE.md` contract (including `raw_headers`, `domain_intel`, and `text_summary`).

#### 2. Endpoint: `GET /api/v1/cases/{case_id}/graph`
Proxies graph topology data from Neo4j (read-only query) into `NetworkGraphData` format for Cytoscape visualizer:
```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "nodes": [
    {"id": "email_1", "label": "Email", "type": "EMAIL", "properties": {"subject": "Urgent Invoice"}}
  ],
  "edges": [
    {"id": "e1", "source": "email_1", "target": "sender_1", "relationship": "HAS_SENDER"}
  ]
}
```

#### 3. Endpoint: `GET /api/v1/reports/{case_id}/export?format=pdf` (or `format=json&include_raw_headers=true`)
Outputs a binary PDF stream generated via ReportLab containing full tamper-evident chain-of-custody headers, risk matrix graphics, and hop trace tables, or returns full JSON export including raw headers.

---

## 4. Local Environment Variables (`.env`)

```bash
# Gateway & Server Config
SERVER_HOST="0.0.0.0"
SERVER_PORT=8000
SECRET_KEY="production_grade_jwt_secret_change_in_prod"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Celery & Redis Configuration
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/1"

# Database Read-Only Connections (Used by API Gateway for case polling & graph proxy endpoints)
POSTGRES_URL="postgresql://postgres:postgres@localhost:5432/sih_forensics"
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password"

# File Storage Configuration (Shared Volume Staging)
EVIDENCE_STAGING_DIR="/tmp/sih_evidence_staging"
PDF_OUTPUT_DIR="/tmp/sih_pdf_reports"
MAX_UPLOAD_SIZE_BYTES=26214400 # 25 MB
```

---

## 5. Isolated Running & Testing Commands

To run and verify Module 2 in total isolation on any machine:

```bash
# 1. Start Redis Server locally or via Docker
docker run -d -p 6379:6379 --name sih_redis redis:alpine

# 2. Install Python Dependencies
pip install -r requirements.txt

# 3. Start Celery Worker Process
celery -A app.core.celery_app worker --loglevel=info -Q default,forensic_tasks

# 4. Start FastAPI Gateway Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. Run Test Suite
pytest tests/ -v
```

---

## 6. Zero-Coupling Cross-Module Fault Isolation Rules

1. **Decoupled Messaging Queues:** Module 2 interacts with backend engines exclusively via Redis task named queues (`queue_header_forensics`, `queue_geoip_intel`, `queue_nlp_fraud`, `queue_graph_attribution`). No direct HTTP coupling exists between Module 2 and the engine modules.
2. **Worker Failure Handling:** If a Celery worker crashes, Redis retains the task message and re-dispatches it to another available worker node without dropping client requests.
3. **Data Sanitization:** Module 2 strips PII from error messages before returning JSON error payloads to Module 1.
