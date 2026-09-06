# CLAUDE.md: Synced Memory & Module Isolation Interface Contract
## Module 4: GeoIP & Domain Infrastructure Intel Engine

---

## 1. Module Overview & Memory Context
* **Module ID:** `MOD-04`
* **Purpose:** Origin IP Isolation, GeoIP Resolution, Infrastructure Threat Flags (Tor/VPN/Proxy), WHOIS Domain Age, Typosquatting Detection.
* **Current Version:** `1.0.0-prod`
* **Owner:** Member 4 (Backend Dev 2)
* **Ingress Queue:** `queue_geoip_intel`
* **Orchestrator Target:** Module 2 (Mediator Celery Chord)

---

## 2. Ingress Interface Schema (Task Arguments from Module 2)

Module 4 listens on Celery signature `tasks.module4_geoip_analysis`.

**Task Parameter Signature:**
```python
def module4_geoip_analysis(case_id: str, file_path: str, raw_hop_chain: list[str] | None = None) -> dict[str, Any]:
    ...
```

* `case_id`: UUID string identifying the investigation case.
* `file_path`: Local disk path to the staged raw `.eml` or `.msg` file.
* `raw_hop_chain`: (Optional) IP address list. When `raw_hop_chain` is `None` (as occurs during parallel Celery chord execution), Module 4 independently parses `Received` headers from the file at `file_path`.

---

## 3. Egress Interface Schema (Return Payload to Module 2)

Module 4 MUST return a dictionary adhering to this exact JSON schema upon task completion:

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

---

## 4. Local Environment Variables (`.env`)

```bash
# Redis Queue Target
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/1"

# GeoIP Local Databases
GEOIP_CITY_DB_PATH="data/GeoLite2-City.mmdb"
GEOIP_ASN_DB_PATH="data/GeoLite2-ASN.mmdb"

# Threat Intelligence APIs (Optional Fallback)
ABUSEIPDB_API_KEY="sample_abuseipdb_api_key_for_dev"
HTTP_TIMEOUT_SECONDS=2.0

# Staging Storage
EVIDENCE_STAGING_DIR="/tmp/sih_evidence_staging"
```

---

## 5. Isolated Running & Testing Commands

To run and verify Module 4 in total isolation:

```bash
# 1. Ensure Redis is running
docker run -d -p 6379:6379 --name sih_redis redis:alpine

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Start Module 4 Celery Worker
celery -A app.core.celery_app worker --loglevel=info -Q queue_geoip_intel

# 4. Run Pytest Suite
pytest tests/ -v
```

---

## 6. Zero-Coupling Cross-Module Fault Isolation Rules

1. **Local MMDB Priority:** Always attempt local MMDB binary disk lookups first before attempting network API queries to ensure offline operation capability during judging/testing.
2. **Strict Execution Timeouts:** Outbound WHOIS/API calls must abort after 2.0 seconds.
3. **No Direct Database Writes:** Module 4 does not write directly to PostgreSQL or Neo4j. All gathered threat metadata is passed back in the return payload to Module 2 for Module 6 to persist.
