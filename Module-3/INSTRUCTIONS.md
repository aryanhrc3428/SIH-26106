# INSTRUCTIONS.md: AI Agent Designing & Coding Standards
## Module 3: Header Parsing & Protocol Forensics Engine

---

## 1. Module Identity & Architectural Boundary
* **Module Name:** `module-3-header-forensics`
* **Owner:** Member 3 (Backend Dev 1)
* **Framework Stack:** Python 3.11+, Celery, Redis, `eml_parser`, `mailparser`, `extract-msg`, `dkimpy`, `dnspython`, Pydantic V2.
* **Core Function:** Conducts RFC 822/2822 deep header parsing, extracts and orders multi-hop transmission chains (`Received` headers), validates SPF/DKIM/DMARC protocols, detects relay manipulation/spoofing, extracts `subject`, `timestamp`, `attachment_hashes`, and `raw_headers`, and evaluates sender identity alignment.
* **Isolation Guarantee:** Module 3 operates strictly as a decoupled background worker consuming tasks from Redis queue `queue_header_forensics`. It **NEVER** exposes HTTP endpoints directly and **NEVER** interacts directly with Module 1, Module 4, Module 5, or Module 6.

---

## 2. Directory Structure & Code Layout Guidelines

When generating or editing code for Module 3, strictly follow this layout:

```
module-3-header-forensics/
├── app/
│   ├── worker.py                   # Celery worker entrypoint & task definitions
│   ├── core/
│   │   ├── config.py               # Pydantic settings for DNS timeouts and worker concurrency
│   │   └── celery_app.py           # Celery application instance configured for queue_header_forensics
│   ├── parsers/
│   │   ├── eml_parser.py           # MIME structure parser & header normalization
│   │   └── msg_parser.py           # MS-Outlook .msg file header converter (extract-msg)
│   ├── forensics/
│   │   ├── hop_extractor.py        # Received header ordering algorithm (bottom-to-top)
│   │   ├── dkim_verifier.py        # Cryptographic DKIM-Signature verification using dkimpy
│   │   ├── spf_verifier.py         # SPF policy evaluation & envelope alignment
│   │   ├── dmarc_verifier.py       # DMARC TXT record querying & alignment enforcement
│   │   └── sender_alignment.py     # Display name vs. Envelope/Header From discrepancy analyzer
│   ├── schemas/
│   │   └── output_schema.py        # Strict Pydantic output model for task completion payload
│   └── utils/
│       ├── dns_resolver.py         # dnspython wrapper with caching & 2.0s strict timeouts
│       └── hashing.py              # SHA-256 and MD5 generation for raw email content
├── tests/
│   ├── test_eml_parser.py
│   ├── test_hop_extractor.py
│   ├── test_dkim_spf.py
│   └── fixtures/                   # Sample .eml files (Pass, Fail, Spoofed, Multi-hop)
├── requirements.txt
└── Dockerfile
```

---

## 3. Designing & Coding Standards

### A. Header Parsing & Hop Chain Extraction Logic
1. **RFC Compliance:** Support standard and non-standard MIME headers (`Received`, `Return-Path`, `Message-ID`, `X-Originating-IP`, `X-Sender`, `Authentication-Results`).
2. **Hop Extraction Rules (Chronological Reconstruction):**
   * Extract all `Received` header instances.
   * Parse in **bottom-to-top order** (the bottom-most `Received` header represents the initial hop from client to first mail transfer agent).
   * Extract IPv4 addresses using `(?:[0-9]{1,3}\.){3}[0-9]{1,3}` and IPv6 addresses using `(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}`.
   * Strip whitespace, comments enclosed in parentheses `(...)`, and bracketed tokens `[...]`.
3. **Cryptographic Hashing & Metadata Extraction:**
   * Compute `sha256` and `md5` hashes over the entire raw EML file stream before parsing to ensure evidentiary integrity.
   * Extract `subject`, `timestamp` (`Date:` header in ISO 8601 format), attachment MIME info (`attachment_hashes`), and retain complete `raw_headers` string.

### B. Protocol Verification (SPF, DKIM, DMARC)
1. **DKIM Verification:**
   * Use `dkimpy` (`dkim.verify()`) to cryptographically validate signatures against public keys retrieved via DNS TXT records (`selector._domainkey.domain`).
   * Handle multi-signature edge cases gracefully.
2. **SPF Alignment Check:**
   * Validate whether the sending IP matches authorized SPF record mechanisms (`ip4`, `ip6`, `a`, `mx`, `include`).
   * Classify results into standard SPF statuses: `PASS`, `FAIL`, `SOFTFAIL`, `NEUTRAL`, `NONE`, `TEMPERROR`, `PERMERROR`.
3. **DMARC Policy Enforcement:**
   * Fetch DMARC TXT record (`_dmarc.domain`).
   * Evaluate DKIM and SPF domain alignment against `Header-From`.
   * Record alignment boolean (`true` if SPF or DKIM domain matches `Header-From`).

### C. Sender Identity Alignment & Display Name Spoofing
1. Compare `Header-From` (`From: Executive Name <exec@company.com>`) against `Envelope-From` (`Return-Path`).
2. Flag display name spoofing if:
   * Display name contains an email address that differs from the actual domain in `Header-From`.
   * Display name matches known VIP/Executive name patterns, but domain is a freemail domain (`gmail.com`, `yahoo.com`) or lookalike domain.

---

## 4. Error Handling & Guardrails

1. **DNS Timeout Guardrails (CRITICAL):**
   * All DNS queries (`dnspython`) MUST enforce explicit `lifetime=2.0` seconds and `timeout=2.0` seconds.
   * If DNS query times out, return status `NONE` or `TEMPERROR` for SPF/DMARC rather than hanging worker execution.
2. **Malformed Header Resilience:**
   * Wrap header parsing in try-except blocks per header key. If a header is malformed, log an anomaly flag and continue processing remaining headers.
3. **Anomalous Score Calculation & Clamping:**
   * `header_anomaly_score` (0.0 to 100.0) calculated dynamically based on weights:
     * SPF Fail: +25
     * DKIM Fail: +25
     * DMARC Fail: +20
     * Display Name Spoofed: +20
     * Forged/Missing Message-ID: +10
   * **Score Clamping:** Standardize score output using `header_anomaly_score = min(calculated_score, 100.0)`.

---

## 5. Testing & Quality Requirements

1. Test coverage must include valid, spoofed, and malformed header fixtures.
2. Run test suite:
   ```bash
   pytest tests/ -v --cov=app
   ```
