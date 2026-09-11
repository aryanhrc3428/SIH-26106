# INSTRUCTIONS.md: Module 5 Agent Build Brief
## NLP Fraud Classifier and Content Analysis Engine

---

## 1. Mission

Build the Celery worker that performs email content analysis for SIH 26106. Module 5 receives a case id and staged evidence path from Module 2, extracts readable body text, sanitizes HTML, detects social engineering language, classifies fraud intent, inspects URLs safely, and returns a typed risk payload.

This module must be fully buildable without Modules 1, 2, 3, 4, or 6 running. Use `CLAUDE.md` as the source of truth for the task signature and result payload.

---

## 2. Architecture Boundary

* Build inside `Module-5/`.
* Do not create a nested project directory.
* Do not import code from sibling module directories.
* Do not expose HTTP endpoints.
* Do not write to databases or graph stores.
* Do not call Module 4 for domain age; return `domain_age_days=null` for URLs.
* All model and network behavior must be mockable in tests.

---

## 3. Required Stack

* Python 3.11+
* Celery
* Redis
* Pydantic V2
* ONNX Runtime or PyTorch
* HuggingFace tokenizer support
* BeautifulSoup with `lxml`
* `httpx`
* `tldextract`
* Pytest

---

## 4. File Layout

Create this layout directly under `Module-5/`:

```text
app/
  worker.py
  core/config.py
  core/celery_app.py
  nlp/text_extractor.py
  nlp/classifier.py
  nlp/urgency_detector.py
  nlp/url_analyzer.py
  nlp/redirect_resolver.py
  schemas/output_schema.py
  utils/model_loader.py
  utils/network_guard.py
contracts/
  module5-nlp-result.sample.json
models/
  README.md
tests/
  fixtures/benign.eml
  fixtures/bec_wire_transfer.eml
  fixtures/credential_harvest.eml
  fixtures/html_obfuscated.eml
  test_text_extractor.py
  test_classifier.py
  test_urgency_detector.py
  test_url_analyzer.py
  test_redirect_resolver.py
  test_worker_task.py
requirements.txt
Dockerfile
```

If a real model file is too large to commit, document how to place it in `models/README.md`. Tests must pass with a small deterministic mock classifier.

---

## 5. Input and Output Mapping

### Inputs Consumed

| Source | Transport | Data | Local owner |
| --- | --- | --- | --- |
| Module 2 | Celery task `tasks.module5_nlp_analysis` | `case_id`, `file_path` | `app/worker.py` |
| Local file | Staged `.eml` or `.msg` | text/plain, text/html, URLs | `nlp/text_extractor.py` |
| Local model | ONNX or mocked classifier | classification and confidence | `nlp/classifier.py`, `utils/model_loader.py` |
| Optional network | Redirect targets | final URL and redirect risk | `nlp/redirect_resolver.py` |

### Outputs Produced

| Destination | Transport | Data | Required behavior |
| --- | --- | --- | --- |
| Module 2 | Celery result | Content analysis payload from `CLAUDE.md` | Always Pydantic-validated |
| Module 2 | Celery result | Degraded/failure payload | Include sanitized `error` only |

---

## 6. Implementation Requirements

1. Extract `text/plain` body first and use sanitized `text/html` as fallback.
2. Strip scripts, styles, hidden zero-size text, tracking pixels, and control characters.
3. Normalize whitespace and decode HTML entities.
4. Truncate classifier input to `MAX_TOKEN_LENGTH` tokens.
5. Load the model once per worker process through a singleton model loader.
6. Provide deterministic fallback classification when `ALLOW_MODEL_FALLBACK=true` and the model file is absent.
7. Detect urgency and BEC patterns with lexical rules in addition to model confidence.
8. Extract URLs from text and HTML links.
9. Resolve redirects up to `MAX_REDIRECT_HOPS`.
10. Before each redirect request, resolve the target host and block private, loopback, link-local, multicast, reserved, CGNAT, and metadata IP ranges.
11. Flag suspicious TLDs: `.top`, `.work`, `.xyz`, `.click`, `.zip`, `.tk`.
12. Calculate and clamp `content_suspicion_score`.
13. Return `DEGRADED` for model or redirect failures and `FAILED` only when evidence cannot be read.

---

## 7. SSRF Guardrails

Block redirect requests to:

* RFC 1918 private ranges
* Loopback ranges
* Link-local ranges
* CGNAT `100.64.0.0/10`
* Cloud metadata IP `169.254.169.254`
* Multicast and reserved ranges
* Hostnames that resolve only to blocked IPs

Tests must verify that blocked destinations are never requested over HTTP.

---

## 8. Testing Requirements

Write tests for:

* Plain-text extraction
* HTML sanitization and hidden text removal
* Body text truncation
* Classifier success and fallback paths
* Urgency/BEC lexical scoring
* URL extraction from text and HTML anchors
* Redirect limit enforcement
* SSRF blocking before redirect requests
* Suspicious TLD scoring
* Worker task success, degraded, and failed outputs

---

## 9. Environment Variables

```bash
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/1"
CELERY_TASK_ALWAYS_EAGER="false"
ONNX_MODEL_PATH="models/deberta_phishing_v1.onnx"
ALLOW_MODEL_FALLBACK="true"
MAX_TOKEN_LENGTH="512"
HTTP_TIMEOUT_SECONDS="2.0"
MAX_REDIRECT_HOPS="5"
EVIDENCE_STAGING_DIR="/tmp/sih_evidence_staging"
```

---

## 10. Independent Compile Gate

Run these commands from `Module-5/` before handing off:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
pytest tests/ -v --cov=app
python -c "from app.core.celery_app import celery_app; print(celery_app.main)"
```

The test suite must pass with local fixtures, mocked redirect requests, model fallback enabled, and no sibling modules running.
