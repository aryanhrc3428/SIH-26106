# CLAUDE.md: Module 5 Interface Contract
## Module 5: NLP Fraud Classifier and Content Analysis Engine

---

## 1. Contract Purpose

This file is the memory contract for the agent building Module 5. Keep only information required to build the content-analysis worker independently and integrate with Module 2 later.

* **Module ID:** `MOD-05`
* **Build root:** `Module-5/` (create app files directly here; do not create a nested `module-5-nlp-fraud/` directory)
* **Primary role:** Extract email body text, sanitize HTML, detect social engineering cues, classify fraud type, inspect URLs, resolve redirect chains safely, and score content risk
* **Consumes from:** Module 2 Celery task arguments
* **Produces to:** Module 2 Celery result payload
* **Never depends on:** Module 1, Module 3, Module 4, Module 6, databases, graph storage, or direct header-forensics output

Before coding, read `../Architecture_and_Plan.md` and `INSTRUCTIONS.md`.

---

## 2. Required Independence

Module 5 must compile, run, and pass tests without any other module running.

* Parse body text and URLs from `file_path` locally.
* Use a mockable classifier wrapper; tests must not require a large downloaded model.
* If the ONNX model is absent in standalone mode, use a deterministic lightweight fallback classifier for tests and local demos.
* All redirect expansion must enforce SSRF protections before each request.
* Never write to PostgreSQL, Neo4j, or Elasticsearch.

---

## 3. Input Mapping: Task Arguments from Module 2

**Task name:** `tasks.module5_nlp_analysis`

**Queue:** `queue_nlp_fraud`

```python
def module5_nlp_analysis(case_id: str, file_path: str) -> dict[str, object]:
    ...
```

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `case_id` | `str` | Yes | Case UUID assigned by Module 2 |
| `file_path` | `str` | Yes | Path to staged `.eml` or `.msg` evidence file under `EVIDENCE_STAGING_DIR` |

---

## 4. Output Mapping: Result Returned to Module 2

Return this shape for successful analysis.

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

### 4.1 Field Rules

| Field | Rule |
| --- | --- |
| `status` | `SUCCESS`, `DEGRADED`, or `FAILED` |
| `content_suspicion_score` | Float from `0.0` to `100.0`, clamped |
| `classification` | `LEGITIMATE`, `PHISHING`, `BEC_FINANCIAL`, `CREDENTIAL_HARVESTING`, `IMPERSONATION`, or `UNKNOWN` |
| `confidence` | Float from `0.0` to `1.0` |
| `detected_language` | ISO language code when detected, otherwise `null` |
| `urgency_score` | Float from `0.0` to `100.0`, clamped |
| `text_summary` | Short sanitized summary, never raw full body |
| `extracted_urls` | Empty array when no URLs are found |
| `domain_age_days` | Always `null`; Module 4 owns WHOIS/domain age |

### 4.2 Failure Shape

If the file is readable but text extraction or model inference is incomplete, return `DEGRADED` with fallback fields:

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "DEGRADED",
  "content_suspicion_score": 0.0,
  "classification": "UNKNOWN",
  "confidence": 0.0,
  "detected_language": null,
  "urgency_score": 0.0,
  "text_summary": null,
  "extracted_urls": [],
  "error": {
    "code": "CONTENT_ANALYSIS_DEGRADED",
    "message": "Content analysis could not complete all checks.",
    "recoverable": true
  }
}
```

Use `FAILED` only when the task cannot read the evidence file.

---

## 5. Scoring Contract

Calculate `content_suspicion_score` using these weights, then clamp at `100.0`.

| Signal | Weight |
| --- | ---: |
| Model class is phishing, BEC, credential harvesting, or impersonation | `60 * confidence` |
| `urgency_score > 70` | 25 |
| Suspicious TLD or shortened URL detected | 15 |

---

## 6. Standalone Completion Gate

Module 5 is ready only when these pass from inside `Module-5/`:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
pytest tests/ -v --cov=app
python -c "from app.core.celery_app import celery_app; print(celery_app.main)"
```

The test suite must pass with local fixtures, mocked network calls, and no sibling modules running.
