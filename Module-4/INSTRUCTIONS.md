# INSTRUCTIONS.md: Module 4 Agent Build Brief
## GeoIP and Domain Infrastructure Intelligence Engine

---

## 1. Mission

Build the Celery worker that performs infrastructure intelligence for SIH 26106. Module 4 receives a case id, staged evidence path, and optional hop chain from Module 2. It identifies the earliest reliable public origin IP, enriches relay hops with GeoIP and ASN data, flags suspicious infrastructure, inspects sender-domain registration signals, and returns a typed payload.

This module must be fully buildable without Modules 1, 2, 3, 5, or 6 running. Use `CLAUDE.md` as the source of truth for the task signature and result payload.

---

## 2. Architecture Boundary

* Build inside `Module-4/`.
* Do not create a nested project directory.
* Do not import code from sibling module directories.
* Do not expose HTTP endpoints.
* Do not write to databases or graph stores.
* Do not require Module 3 output; parse headers locally when `raw_hop_chain` is missing.
* All external lookup clients must be wrapped so tests can run offline.

---

## 3. Required Stack

* Python 3.11+
* Celery
* Redis
* Pydantic V2
* `geoip2`
* `python-whois`
* `dnspython`
* `httpx`
* `ipaddress`
* Pytest

---

## 4. File Layout

Create this layout directly under `Module-4/`:

```text
app/
  worker.py
  core/config.py
  core/celery_app.py
  intel/header_reader.py
  intel/ip_filter.py
  intel/geoip_resolver.py
  intel/threat_infra.py
  intel/whois_checker.py
  intel/typosquat_checker.py
  schemas/output_schema.py
  utils/http_client.py
  utils/ip_utils.py
contracts/
  module4-geoip-result.sample.json
data/
  GeoLite2-City.mmdb
  GeoLite2-ASN.mmdb
  tor_exit_nodes.txt
  target_brands.json
tests/
  fixtures/multihop.eml
  test_header_reader.py
  test_ip_filter.py
  test_geoip_resolver.py
  test_threat_infra.py
  test_whois_checker.py
  test_typosquat_checker.py
  test_worker_task.py
requirements.txt
Dockerfile
```

Large binary MMDB files may be documented as setup prerequisites if they are too large to commit. Tests must pass without them by mocking the resolver or using a tiny local fixture.

---

## 5. Input and Output Mapping

### Inputs Consumed

| Source | Transport | Data | Local owner |
| --- | --- | --- | --- |
| Module 2 | Celery task `tasks.module4_geoip_analysis` | `case_id`, `file_path`, optional `raw_hop_chain` | `app/worker.py` |
| Local file | Staged `.eml` or `.msg` | `Received` headers and sender domain | `intel/header_reader.py` |
| Local data | MMDB, Tor list, target brand list | GeoIP, Tor, typosquat enrichment | `data/` |
| Optional external lookup | WHOIS, AbuseIPDB-style API | Domain and abuse enrichment | wrapped service clients |

### Outputs Produced

| Destination | Transport | Data | Required behavior |
| --- | --- | --- | --- |
| Module 2 | Celery result | GeoIP/domain payload from `CLAUDE.md` | Always Pydantic-validated |
| Module 2 | Celery result | Degraded/failure payload | Include sanitized `error` only |

---

## 6. Implementation Requirements

1. Normalize hop-chain input into chronological order, origin first.
2. When `raw_hop_chain` is `None`, parse all `Received` headers from `file_path`.
3. Filter private, loopback, link-local, multicast, reserved, CGNAT, and documentation ranges with `ipaddress`.
4. Select the earliest IP where `ipaddress.ip_address(value).is_global` is true.
5. Resolve city, country, latitude, longitude, ASN, and ISP from local MMDB readers when available.
6. Return deterministic `UNKNOWN` or `null` fields when MMDB data is absent.
7. Match Tor exit nodes from `data/tor_exit_nodes.txt`.
8. Flag likely VPN/proxy/cloud relay infrastructure from local indicators first, then optional API data.
9. Extract sender domain locally from headers and perform WHOIS age checks with timeouts.
10. Detect typosquatting with Levenshtein distance and IDN homograph/punycode checks.
11. Calculate and clamp `geo_risk_score`.
12. Return `DEGRADED` for missing enrichment and `FAILED` only when evidence cannot be read.

Do not use RFC 5737 documentation IP ranges such as `192.0.2.0/24`, `198.51.100.0/24`, or `203.0.113.0/24` as positive public-origin tests because Python may correctly reject them as non-global.

---

## 7. Timeout and Offline Rules

* WHOIS timeout: `2.0` seconds.
* HTTP timeout: `2.0` seconds.
* If WHOIS fails, set `domain_age_days=null` and continue.
* If MMDB is unavailable, keep hop rows and fill GeoIP fields with `UNKNOWN` or `null`.
* Tests must not depend on live WHOIS, live HTTP, or real MaxMind databases.

---

## 8. Testing Requirements

Write tests for:

* Public versus private IP filtering
* CGNAT, loopback, link-local, multicast, and reserved IP rejection
* Header parsing fallback when `raw_hop_chain` is missing
* Earliest reliable public IP selection
* MMDB success and missing-file fallback
* Tor node matching
* VPN/proxy/cloud relay matching
* WHOIS age calculation and timeout fallback
* Typosquat and punycode homograph detection
* Worker task success, degraded, and failed outputs

---

## 9. Environment Variables

```bash
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/1"
CELERY_TASK_ALWAYS_EAGER="false"
GEOIP_CITY_DB_PATH="data/GeoLite2-City.mmdb"
GEOIP_ASN_DB_PATH="data/GeoLite2-ASN.mmdb"
ABUSEIPDB_API_KEY=""
HTTP_TIMEOUT_SECONDS="2.0"
WHOIS_TIMEOUT_SECONDS="2.0"
EVIDENCE_STAGING_DIR="/tmp/sih_evidence_staging"
```

Do not commit real API keys.

---

## 10. Independent Compile Gate

Run these commands from `Module-4/` before handing off:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
pytest tests/ -v --cov=app
python -c "from app.core.celery_app import celery_app; print(celery_app.main)"
```

The test suite must pass with mocked lookups and no sibling modules running.
