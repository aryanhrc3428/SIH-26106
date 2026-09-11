# CLAUDE.md: Module 3 Interface Contract
## Module 3: Header Parsing and Protocol Forensics Engine

---

## 1. Contract Purpose

This file is the memory contract for the agent building Module 3. Keep only information required to build the header forensics worker independently and integrate with Module 2 later.

* **Module ID:** `MOD-03`
* **Build root:** `Module-3/` (create app files directly here; do not create a nested `module-3-header-forensics/` directory)
* **Primary role:** Parse raw `.eml` and `.msg` evidence, extract headers and attachment hashes, reconstruct hop chains, verify SPF/DKIM/DMARC, and score header anomalies
* **Consumes from:** Module 2 Celery task arguments
* **Produces to:** Module 2 Celery result payload
* **Never depends on:** Module 1, Module 4, Module 5, Module 6, databases, HTTP APIs, or graph storage

Before coding, read `../Architecture_and_Plan.md` and `INSTRUCTIONS.md`.

---

## 2. Required Independence

Module 3 must compile, run, and pass tests without any other module running.

* Accept only serialized Celery task arguments and local evidence files.
* Include local `.eml` fixtures for valid, spoofed, malformed, and multi-hop cases.
* Unit tests must call parsing services and the Celery task directly in eager mode.
* DNS lookups must have strict timeouts and mockable resolver wrappers.
* No direct HTTP requests are allowed.

---

## 3. Input Mapping: Task Arguments from Module 2

**Task name:** `tasks.module3_header_analysis`

**Queue:** `queue_header_forensics`

```python
def module3_header_analysis(case_id: str, file_path: str) -> dict[str, object]:
    ...
```

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `case_id` | `str` | Yes | Case UUID assigned by Module 2 |
| `file_path` | `str` | Yes | Path to staged `.eml` or `.msg` evidence file under `EVIDENCE_STAGING_DIR` |

Input file rules:

* `.eml` files must be parsed as RFC 822/2822 messages.
* `.msg` files must be converted with `extract-msg` or an equivalent local parser before header analysis.
* Hashes must be calculated from the original raw file bytes before parsing or conversion.

---

## 4. Output Mapping: Result Returned to Module 2

Return this shape for successful analysis.

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
  "spf": {
    "status": "FAIL",
    "domain": "spoofed-bank.com",
    "ip": "192.0.2.1"
  },
  "dkim": {
    "status": "FAIL",
    "selector": "s1",
    "domain": "spoofed-bank.com"
  },
  "dmarc": {
    "status": "FAIL",
    "policy": "reject",
    "alignment": false
  },
  "sender_alignment": {
    "header_from": "billing@legitbank.com",
    "envelope_from": "spammer@evil-server.net",
    "reply_to": "attacker@harvest-site.org",
    "is_display_name_spoofed": true,
    "spoofed_entity_detected": "Legitimate Bank Executive"
  },
  "raw_hop_chain": [
    "192.0.2.1",
    "198.51.100.25",
    "203.0.113.195"
  ],
  "raw_headers": "Received: from relay01.evil-server.net...\nFrom: CEO <billing@legitbank.com>..."
}
```

### 4.1 Field Rules

| Field | Rule |
| --- | --- |
| `status` | `SUCCESS`, `DEGRADED`, or `FAILED` |
| `timestamp` | ISO 8601 UTC if parsable, otherwise `null` with `status=DEGRADED` |
| `hashes.sha256` | Required for any readable file |
| `hashes.md5` | Required for compatibility with forensic tools |
| `attachment_hashes` | Empty array when there are no attachments |
| `raw_hop_chain` | Chronological order, origin first, destination last |
| `raw_headers` | Complete raw header block only, not full body |
| `header_anomaly_score` | Float from `0.0` to `100.0`, clamped |

### 4.2 Failure Shape

If the file cannot be read or parsed enough to calculate hashes, return:

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "FAILED",
  "error": {
    "code": "UNREADABLE_EVIDENCE",
    "message": "Evidence file could not be read or parsed.",
    "recoverable": false
  }
}
```

If the file is readable but one protocol check fails because of timeout or malformed DNS data, return `status=DEGRADED` and include every field that can be safely computed.

---

## 5. Scoring Contract

Calculate `header_anomaly_score` using these weights, then clamp at `100.0`.

| Signal | Weight |
| --- | ---: |
| SPF `FAIL` or `PERMERROR` | 25 |
| DKIM `FAIL` | 25 |
| DMARC `FAIL` | 20 |
| Display name spoofing | 20 |
| Forged or missing `Message-ID` | 10 |

---

## 6. Standalone Completion Gate

Module 3 is ready only when these pass from inside `Module-3/`:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
pytest tests/ -v --cov=app
python -c "from app.core.celery_app import celery_app; print(celery_app.main)"
```

The test suite must pass with local fixtures and no sibling modules running.
