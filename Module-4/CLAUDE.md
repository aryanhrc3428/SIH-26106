# CLAUDE.md: Module 4 Interface Contract
## Module 4: GeoIP and Domain Infrastructure Intelligence Engine

---

## 1. Contract Purpose

This file is the memory contract for the agent building Module 4. Keep only information required to build the GeoIP/domain intelligence worker independently and integrate with Module 2 later.

* **Module ID:** `MOD-04`
* **Build root:** `Module-4/` (create app files directly here; do not create a nested `module-4-geoip-intel/` directory)
* **Primary role:** Identify reliable public origin IPs, resolve GeoIP/ASN metadata, flag Tor/VPN/proxy/cloud infrastructure, inspect sender domain age and typosquatting, and score infrastructure risk
* **Consumes from:** Module 2 Celery task arguments
* **Produces to:** Module 2 Celery result payload
* **Never depends on:** Module 1, Module 3, Module 5, Module 6, graph storage, NLP models, or database writes

Before coding, read `../Architecture_and_Plan.md` and `INSTRUCTIONS.md`.

---

## 2. Required Independence

Module 4 must compile, run, and pass tests without any other module running.

* If `raw_hop_chain` is not provided, parse `Received` headers from `file_path` locally.
* Extract sender domain from the staged file locally; do not wait for Module 3 output.
* Use local MaxMind `.mmdb` files when present, with deterministic fallback values when absent.
* Mock WHOIS, DNS, Tor lists, and HTTP API calls in tests.
* Never write to PostgreSQL, Neo4j, or Elasticsearch.

---

## 3. Input Mapping: Task Arguments from Module 2

**Task name:** `tasks.module4_geoip_analysis`

**Queue:** `queue_geoip_intel`

```python
def module4_geoip_analysis(
    case_id: str,
    file_path: str,
    raw_hop_chain: list[str] | None = None,
) -> dict[str, object]:
    ...
```

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `case_id` | `str` | Yes | Case UUID assigned by Module 2 |
| `file_path` | `str` | Yes | Path to staged `.eml` or `.msg` evidence file under `EVIDENCE_STAGING_DIR` |
| `raw_hop_chain` | `list[str] | None` | No | Chronological hop IP list. When missing, Module 4 must parse `Received` headers itself |

---

## 4. Output Mapping: Result Returned to Module 2

Return this shape for successful analysis.

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "geo_risk_score": 90.0,
  "earliest_reliable_ip": "93.184.216.34",
  "origin_country": "US",
  "origin_city": "Los Angeles",
  "hops": [
    {
      "hop_index": 1,
      "ip": "93.184.216.34",
      "hostname": "relay01.suspicious-example.net",
      "country": "US",
      "city": "Los Angeles",
      "latitude": 34.0522,
      "longitude": -118.2437,
      "isp": "Example Hosting LLC",
      "asn": "AS15133",
      "is_vpn_or_proxy": true,
      "is_tor_exit_node": false,
      "delay_from_prev_ms": 0
    }
  ],
  "domain_intel": {
    "domain": "suspicious-example.net",
    "domain_age_days": 12,
    "registrar": "Example Registrar Inc.",
    "is_newly_registered": true,
    "is_typosquatted": true,
    "target_brand_spoofed": "microsoft.com"
  }
}
```

### 4.1 Field Rules

| Field | Rule |
| --- | --- |
| `status` | `SUCCESS`, `DEGRADED`, or `FAILED` |
| `geo_risk_score` | Float from `0.0` to `100.0`, clamped |
| `earliest_reliable_ip` | First public global IP in chronological hop order, or `null` when none is reliable |
| `origin_country`, `origin_city` | `UNKNOWN` or `null` when GeoIP data is unavailable |
| `hops` | Empty array only when no public hop can be extracted |
| `domain_intel.domain_age_days` | `null` when WHOIS fails or creation date is unavailable |
| `domain_intel.target_brand_spoofed` | `null` when no typosquat/homograph match is found |

### 4.2 Failure Shape

If no hop chain or sender domain can be extracted, return a degraded payload when possible:

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "DEGRADED",
  "geo_risk_score": 0.0,
  "earliest_reliable_ip": null,
  "origin_country": null,
  "origin_city": null,
  "hops": [],
  "domain_intel": {
    "domain": null,
    "domain_age_days": null,
    "registrar": null,
    "is_newly_registered": false,
    "is_typosquatted": false,
    "target_brand_spoofed": null
  },
  "error": {
    "code": "NO_PUBLIC_ORIGIN",
    "message": "No reliable public origin IP could be extracted.",
    "recoverable": true
  }
}
```

Use `FAILED` only when the task cannot read the evidence file and cannot compute any useful infrastructure result.

---

## 5. Scoring Contract

Calculate `geo_risk_score` using these weights, then clamp at `100.0`.

| Signal | Weight |
| --- | ---: |
| Tor exit node | 40 |
| VPN or anonymous proxy | 25 |
| Domain age under 30 days | 30 |
| Typosquatting or homograph match | 25 |
| High-risk hosting ASN or cloud relay anomaly | 15 |

---

## 6. Standalone Completion Gate

Module 4 is ready only when these pass from inside `Module-4/`:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
pytest tests/ -v --cov=app
python -c "from app.core.celery_app import celery_app; print(celery_app.main)"
```

The test suite must pass with local fixtures and mocked external lookups, with no sibling modules running.
