# INSTRUCTIONS.md: AI Agent Designing & Coding Standards
## Module 4: GeoIP & Domain Infrastructure Intel Engine

---

## 1. Module Identity & Architectural Boundary
* **Module Name:** `module-4-geoip-intel`
* **Owner:** Member 4 (Backend Dev 2)
* **Framework Stack:** Python 3.11+, Celery, Redis, MaxMind `geoip2` / GeoLite2, `python-whois`, `dnspython`, `httpx`, `ipaddress`, Pydantic V2.
* **Core Function:** Isolates public originating IP addresses from hop chains, resolves IP-to-location/ISP/ASN metadata, flags threat infrastructure (Tor, VPN, Proxies, Cloud Relays), conducts WHOIS domain age checks, and calculates `geo_risk_score`.
* **Isolation Guarantee:** Module 4 operates strictly as a background worker consuming tasks from Redis queue `queue_geoip_intel`. It **NEVER** exposes HTTP endpoints directly and **NEVER** interacts directly with Module 1, Module 3, Module 5, or Module 6.

---

## 2. Directory Structure & Code Layout Guidelines

When generating or editing code for Module 4, strictly follow this layout:

```
module-4-geoip-intel/
├── app/
│   ├── worker.py                   # Celery worker entrypoint & task definitions
│   ├── core/
│   │   ├── config.py               # Pydantic settings for GeoIP DB paths & API keys
│   │   └── celery_app.py           # Celery application instance configured for queue_geoip_intel
│   ├── intel/
│   │   ├── ip_filter.py            # RFC 1918 / Loopback / Bogon IP filtering algorithm
│   │   ├── geoip_resolver.py       # MaxMind GeoLite2 MMDB offline reader service
│   │   ├── threat_infra.py         # Tor exit list, VPN, and proxy indicator matcher
│   │   ├── whois_checker.py        # WHOIS domain age & registrar extractor
│   │   └── typosquat_checker.py    # Levenshtein distance & homograph domain analyzer
│   ├── schemas/
│   │   └── output_schema.py        # Strict Pydantic output model for task completion payload
│   └── utils/
│       ├── http_client.py          # Asynchronous HTTP client with 2.0s hard timeouts
│       └── ip_utils.py             # Subnet matching and CIDR helpers
├── data/
│   ├── GeoLite2-City.mmdb          # MaxMind offline city database
│   ├── GeoLite2-ASN.mmdb           # MaxMind offline ASN database
│   ├── tor_exit_nodes.txt          # Cached list of active Tor exit IPs
│   └── target_brands.json          # Dictionary of target corporate domains for typosquatting checks
├── tests/
│   ├── test_ip_filter.py
│   ├── test_geoip_resolver.py
│   ├── test_whois_checker.py
│   └── test_typosquat.py
├── requirements.txt
└── Dockerfile
```

---

## 3. Designing & Coding Standards

### A. IP Extraction & Filtering Logic
1. **Bogon & RFC 1918 Filtering (CRITICAL):**
   * Use Python's `ipaddress` module (`ipaddress.ip_address(ip).is_global`).
   * Filter out private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), link-local (`169.254.0.0/16`), and carrier-grade NAT (`100.64.0.0/10`).
   * If `raw_hop_chain` parameter is `None` (during parallel Celery chord execution), independently parse `Received` headers from the raw EML/MSG file at `file_path`.
   * Select the **earliest reliable public IP address** in the `Received` hop chain as the candidate originating IP.

### B. GeoIP & ASN Resolution
1. **Local MMDB Reader (Sub-Millisecond Performance):**
   * Use MaxMind `geoip2.database.Reader` reading local `.mmdb` binary files for City and ASN lookups.
   * Extracts: Country ISO Code, City Name, Latitude, Longitude, Autonomous System Number (ASN), and Autonomous System Organization (ISP/Host).

### C. Threat Infrastructure & Anomaly Detection
1. **Tor & VPN Detection:**
   * Tor: Match IP against local cached `tor_exit_nodes.txt` list.
   * VPN / Proxy: Query cached AbuseIPDB API or match against known cloud server ASN ranges (AWS AS16509, GCP AS15169, Azure AS8075).
2. **Domain WHOIS & Registration Age:**
   * Extract domain from sender email (`Header-From`).
   * Execute WHOIS query using `python-whois`.
   * Calculate domain creation age in days (`(now - creation_date).days`).
   * Flag domains created less than **30 days** ago as high-risk newly registered domains (NRDs).
3. **Typosquatting & Homograph Detection:**
   * Calculate Levenshtein edit distance between sender domain and target brand domain list in `data/target_brands.json` (e.g., `micros0ft.com` vs `microsoft.com`).
   * Detect IDN homograph punycode attacks (`xn--...`).

---

## 4. Error Handling & Guardrails

1. **WHOIS & External API Timeout Guardrails (CRITICAL):**
   * All outbound WHOIS or HTTP API queries MUST enforce `timeout=2.0` seconds.
   * If WHOIS lookup fails or times out, set `domain_age_days = null` and continue processing without throwing unhandled exceptions.
2. **Offline MMDB Fallback:**
   * If local `.mmdb` file is missing or unreadable, log an error, assign fallback values (`Country: UNKNOWN`, `City: UNKNOWN`), and proceed.
3. **Geo-Risk Score Calculation & Clamping:**
   * `geo_risk_score` (0.0 to 100.0) calculated dynamically based on weights:
     * Tor Exit Node: +40
     * VPN / Anonymous Proxy: +25
     * Domain Creation Age < 30 Days: +30
     * Typosquatting / Homograph Flag: +25
     * High-Risk Country / Hosting ASN: +15
   * **Score Clamping:** Standardize score output using `geo_risk_score = min(calculated_score, 100.0)`.

---

## 5. Testing & Quality Requirements

1. Test coverage must include public IPs, internal private IPs, newly registered domains, and homograph spoofing test cases.
2. Run test suite:
   ```bash
   pytest tests/ -v --cov=app
   ```
