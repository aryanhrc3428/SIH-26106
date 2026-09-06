# CLAUDE.md: Synced Memory & Module Isolation Interface Contract
## Module 5: NLP Fraud Classifier & Content Analysis Engine

---

## 1. Module Overview & Memory Context
* **Module ID:** `MOD-05`
* **Purpose:** Text Extraction, Transformer Fraud Classification, Urgency/BEC Detection, Embedded Link Inspection & Redirect Expansion.
* **Current Version:** `1.0.0-prod`
* **Owner:** Member 5 (Backend Dev 3)
* **Ingress Queue:** `queue_nlp_fraud`
* **Orchestrator Target:** Module 2 (Mediator Celery Chord)

---

## 2. Ingress Interface Schema (Task Arguments from Module 2)

Module 5 listens on Celery signature `tasks.module5_nlp_analysis`.

**Task Parameter Signature:**
```python
def module5_nlp_analysis(case_id: str, file_path: str) -> dict[str, Any]:
    ...
```

* `case_id`: UUID string identifying the investigation case.
* `file_path`: Local disk path to the staged raw `.eml` or `.msg` file.

---

## 3. Egress Interface Schema (Return Payload to Module 2)

Module 5 MUST return a dictionary adhering to this exact JSON schema upon task completion:

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "content_suspicion_score": 92.0,
  "classification": "BEC_FINANCIAL",
  "confidence": 0.96,
  "detected_language": "en",
  "urgency_score": 88.5,
  "extracted_urls": [
    {
      "original_url": "http://bit.ly/3x89aQ",
      "final_redirect_url": "https://credential-harvest-login.com/auth",
      "domain_age_days": null,
      "is_suspicious_tld": true,
      "risk_score": 95.0
    }
  ],
  "text_summary": "Urgent request for wire transfer diversion to updated vendor account."
}
```

---

## 4. Local Environment Variables (`.env`)

```bash
# Redis Queue Target
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/1"

# Model Configuration
ONNX_MODEL_PATH="models/deberta_phishing_v1.onnx"
MAX_TOKEN_LENGTH=512

# URL Unshortening Guardrails
HTTP_TIMEOUT_SECONDS=2.0
MAX_REDIRECT_HOPS=5

# Staging Storage
EVIDENCE_STAGING_DIR="/tmp/sih_evidence_staging"
```

---

## 5. Isolated Running & Testing Commands

To run and verify Module 5 in total isolation:

```bash
# 1. Ensure Redis is running
docker run -d -p 6379:6379 --name sih_redis redis:alpine

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Start Module 5 Celery Worker
celery -A app.core.celery_app worker --loglevel=info -Q queue_nlp_fraud

# 4. Run Pytest Suite
pytest tests/ -v
```

---

## 6. Zero-Coupling Cross-Module Fault Isolation Rules

1. **In-Memory Model Singleton:** Transformer models must be loaded into memory once during worker warm-up to prevent disk I/O bottlenecks.
2. **Non-Blocking Network Unshortening:** URL expansion operates asynchronously via `httpx` with strict 2.0s timeouts so slow malicious servers cannot stall the worker.
3. **No Direct Database Connections:** Module 5 does not write to PostgreSQL or Neo4j. All extracted features and classification scores are returned directly to Module 2.
