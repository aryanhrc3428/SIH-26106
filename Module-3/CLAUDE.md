# CLAUDE.md: Synced Memory & Module Isolation Interface Contract
## Module 3: Header Parsing & Protocol Forensics Engine

---

## 1. Module Overview & Memory Context
* **Module ID:** `MOD-03`
* **Purpose:** RFC Header Parsing, Multi-Hop Chain Extraction, SPF/DKIM/DMARC Protocol Forensics, Display Name Spoofing Detection.
* **Current Version:** `1.0.0-prod`
* **Owner:** Member 3 (Backend Dev 1)
* **Ingress Queue:** `queue_header_forensics`
* **Orchestrator Target:** Module 2 (Mediator Celery Chord)

---

## 2. Ingress Interface Schema (Task Arguments from Module 2)

Module 3 listens on Celery signature `tasks.module3_header_analysis`.

**Task Parameter Signature:**
```python
def module3_header_analysis(case_id: str, file_path: str) -> dict[str, Any]:
    ...
```

* `case_id`: UUID string identifying the investigation case.
* `file_path`: Local disk path to the staged raw `.eml` or `.msg` file.

---

## 3. Egress Interface Schema (Return Payload to Module 2)

Module 3 MUST return a dictionary adhering to this exact JSON schema upon task completion:

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

---

## 4. Local Environment Variables (`.env`)

```bash
# Redis Queue Target
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/1"

# DNS Guardrails
DNS_TIMEOUT_SECONDS=2.0
DNS_CUSTOM_NAMESERVERS="1.1.1.1,8.8.8.8"

# Staging Storage
EVIDENCE_STAGING_DIR="/tmp/sih_evidence_staging"
```

---

## 5. Isolated Running & Testing Commands

To run and verify Module 3 in total isolation:

```bash
# 1. Ensure Redis is running
docker run -d -p 6379:6379 --name sih_redis redis:alpine

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Start Module 3 Celery Worker
celery -A app.core.celery_app worker --loglevel=info -Q queue_header_forensics

# 4. Run Pytest Suite
pytest tests/ -v
```

---

## 6. Zero-Coupling Cross-Module Fault Isolation Rules

1. **Stateless Operations:** Module 3 does not hold database connection pools or maintain session state across tasks. Each task runs independently given a `file_path`.
2. **DNS Cache Isolation:** Use local in-memory LRU caching (`functools.lru_cache`) for DNS lookups within task life to avoid repetitive external lookups.
3. **No Direct HTTP Calls:** Module 3 must never perform outbound HTTP/HTTPS requests to external services. All network activity is restricted exclusively to DNS query calls (`dnspython`).
