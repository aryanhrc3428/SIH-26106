# INSTRUCTIONS.md: Module 3 Agent Build Brief
## Header Parsing and Protocol Forensics Engine

---

## 1. Mission

Build the Celery worker that performs email header forensics for SIH 26106. Module 3 receives a staged raw email path from Module 2, extracts forensic metadata, reconstructs the relay hop chain, verifies sender authentication, detects spoofing, and returns a typed payload.

This module must be fully buildable without Modules 1, 2, 4, 5, or 6 running. Use `CLAUDE.md` as the source of truth for the task signature and result payload.

---

## 2. Architecture Boundary

* Build inside `Module-3/`.
* Do not create a nested project directory.
* Do not import code from sibling module directories.
* Do not expose HTTP endpoints.
* Do not write to databases or graph stores.
* Do not call external HTTP APIs.
* Network access is limited to DNS queries needed for SPF, DKIM, and DMARC, and those queries must be mockable in tests.

---

## 3. Required Stack

* Python 3.11+
* Celery
* Redis
* Pydantic V2
* `eml_parser` or Python stdlib `email`
* `mailparser`
* `extract-msg`
* `dkimpy`
* `dnspython`
* Pytest

---

## 4. File Layout

Create this layout directly under `Module-3/`:

```text
app/
  worker.py
  core/config.py
  core/celery_app.py
  parsers/eml_parser.py
  parsers/msg_parser.py
  forensics/hop_extractor.py
  forensics/dkim_verifier.py
  forensics/spf_verifier.py
  forensics/dmarc_verifier.py
  forensics/sender_alignment.py
  schemas/output_schema.py
  utils/dns_resolver.py
  utils/hashing.py
contracts/
  module3-header-result.sample.json
tests/
  fixtures/legitimate.eml
  fixtures/spoofed.eml
  fixtures/malformed.eml
  fixtures/multihop.eml
  test_eml_parser.py
  test_msg_parser.py
  test_hop_extractor.py
  test_protocol_verifiers.py
  test_sender_alignment.py
  test_worker_task.py
requirements.txt
Dockerfile
```

---

## 5. Input and Output Mapping

### Inputs Consumed

| Source | Transport | Data | Local owner |
| --- | --- | --- | --- |
| Module 2 | Celery task `tasks.module3_header_analysis` | `case_id`, `file_path` | `app/worker.py` |
| Local tests | Fixture files | `.eml`, optional `.msg` samples | `tests/fixtures/` |

### Outputs Produced

| Destination | Transport | Data | Required behavior |
| --- | --- | --- | --- |
| Module 2 | Celery result | Header analysis payload from `CLAUDE.md` | Always Pydantic-validated |
| Module 2 | Celery result | Failure payload | Use sanitized `error.code` and `error.message` |

---

## 6. Implementation Requirements

1. Compute SHA-256 and MD5 from raw bytes before parsing.
2. Parse `.eml` with RFC-compatible header preservation.
3. Convert `.msg` to equivalent header/body structures without mutating the source file.
4. Extract `Subject`, `Date`, `From`, `Return-Path`, `Reply-To`, `Message-ID`, `Authentication-Results`, and all `Received` headers.
5. Reconstruct `raw_hop_chain` from bottom-most `Received` header to top-most `Received` header.
6. Extract valid IPv4 and IPv6 addresses, then leave filtering of private/public IPs to Module 4.
7. Verify DKIM using `dkimpy` and DNS TXT lookup through `utils/dns_resolver.py`.
8. Evaluate SPF and DMARC with DNS timeouts and deterministic fallback statuses.
9. Detect display name spoofing and envelope/header domain mismatch.
10. Calculate and clamp `header_anomaly_score`.
11. Return `DEGRADED` for partial protocol failures and `FAILED` only when the file cannot be read enough to produce forensic evidence.

---

## 7. DNS and Timeout Rules

* Configure DNS resolver `timeout=2.0` and `lifetime=2.0`.
* Wrap DNS failures into `TEMPERROR` or `NONE`.
* Cache DNS lookups in-process with an LRU cache.
* Tests must mock DNS responses; they must not depend on live DNS.

---

## 8. Testing Requirements

Write tests for:

* Raw file hashing
* Header preservation
* Multi-hop ordering
* IPv4 and IPv6 extraction
* SPF pass, fail, none, and temp-error paths
* DKIM pass, fail, and no-signature paths
* DMARC alignment pass and fail paths
* Display name spoofing
* Malformed header resilience
* Worker task success, degraded, and failed outputs

---

## 9. Environment Variables

```bash
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/1"
CELERY_TASK_ALWAYS_EAGER="false"
DNS_TIMEOUT_SECONDS="2.0"
DNS_CUSTOM_NAMESERVERS="1.1.1.1,8.8.8.8"
EVIDENCE_STAGING_DIR="/tmp/sih_evidence_staging"
```

---

## 10. Independent Compile Gate

Run these commands from `Module-3/` before handing off:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
pytest tests/ -v --cov=app
python -c "from app.core.celery_app import celery_app; print(celery_app.main)"
```

The test suite must pass with local fixtures and mocked DNS, with no sibling modules running.
