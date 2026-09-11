# CLAUDE.md: Module 1 Interface Contract
## Module 1: Presentation Layer and Forensic Visualization

---

## 1. Contract Purpose

This file is the memory contract for the agent building Module 1. Keep only information required to build the frontend independently and integrate with Module 2 later.

* **Module ID:** `MOD-01`
* **Build root:** `Module-1/` (create app files directly here; do not create a nested `module-1-frontend/` directory)
* **Primary role:** Analyst web dashboard, upload UI, case investigation workbench, hop map, graph viewer, risk matrix, and report download trigger
* **Consumes from:** Module 2 only
* **Produces to:** Module 2 only
* **Never depends on:** Celery, Redis, PostgreSQL, Neo4j, Elasticsearch, or direct calls to Modules 3, 4, 5, or 6

Before coding, read `../Architecture_and_Plan.md` and `INSTRUCTIONS.md`.

---

## 2. Required Independence

Module 1 must compile, run, and pass tests without any other module running.

* Use Mock Service Worker (MSW) for all Module 2 responses during standalone development.
* Store contract fixtures under `contracts/` or `tests/fixtures/`.
* Route every network call through one typed API client.
* Validate every response with Zod before passing data to React components.
* If Module 2 is unavailable or returns invalid data, render a degraded UI state instead of throwing.

---

## 3. Input Mapping: Data Consumed from Module 2

### 3.1 Upload Response

Module 1 sends files to Module 2 and receives this response.

**Endpoint:** `POST /api/v1/cases/upload`

```typescript
export interface UploadAccepted {
  batch_id: string;
  cases: Array<{
    case_id: string;
    file_name: string;
    sha256_hash: string;
    status: 'PENDING' | 'PROCESSING';
    estimated_duration_ms: number;
  }>;
}
```

### 3.2 Case Analysis

**Endpoint:** `GET /api/v1/cases/{case_id}/analysis`

```typescript
export interface AnalysisResult {
  case_id: string;
  file_name: string;
  sha256_hash: string;
  md5_hash?: string;
  timestamp: string;
  subject?: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'DEGRADED' | 'FAILED';
  processing_time_ms: number;
  raw_headers?: string;
  risk_matrix: RiskMatrix;
  protocol_forensics: ProtocolForensics;
  routing_topology: RoutingTopology;
  content_analysis: ContentAnalysis;
  linked_campaign?: LinkedCampaign | null;
}

export interface RiskMatrix {
  composite_score: number;
  threat_level: 'CLEAN' | 'SUSPICIOUS' | 'HIGH_RISK' | 'CRITICAL';
  breakdown: {
    header_anomaly_score: number;
    content_suspicion_score: number;
    geo_risk_score: number;
    graph_reputation_score: number;
  };
  flags: Array<{
    code: string;
    severity: 'INFO' | 'WARNING' | 'CRITICAL';
    message: string;
    source_module: 'MOD-02' | 'MOD-03' | 'MOD-04' | 'MOD-05' | 'MOD-06';
  }>;
}

export interface ProtocolForensics {
  spf: { status: 'PASS' | 'FAIL' | 'SOFTFAIL' | 'NEUTRAL' | 'NONE' | 'TEMPERROR' | 'PERMERROR'; domain: string | null; ip: string | null };
  dkim: { status: 'PASS' | 'FAIL' | 'NONE' | 'TEMPERROR'; selector: string | null; domain: string | null };
  dmarc: { status: 'PASS' | 'FAIL' | 'NONE' | 'TEMPERROR'; policy: 'reject' | 'quarantine' | 'none' | null; alignment: boolean };
  sender_alignment: {
    header_from: string | null;
    envelope_from: string | null;
    reply_to: string | null;
    is_display_name_spoofed: boolean;
    spoofed_entity_detected: string | null;
  };
}

export interface RoutingTopology {
  total_hops: number;
  earliest_reliable_ip: string | null;
  origin_country: string | null;
  origin_city: string | null;
  hops: Array<{
    hop_index: number;
    ip: string;
    hostname: string | null;
    country: string | null;
    city: string | null;
    latitude: number | null;
    longitude: number | null;
    isp: string | null;
    asn: string | null;
    is_vpn_or_proxy: boolean;
    is_tor_exit_node: boolean;
    delay_from_prev_ms: number | null;
  }>;
  domain_intel?: DomainIntel | null;
}

export interface DomainIntel {
  domain: string | null;
  domain_age_days: number | null;
  registrar: string | null;
  is_newly_registered: boolean;
  is_typosquatted: boolean;
  target_brand_spoofed: string | null;
}

export interface ContentAnalysis {
  classification: 'LEGITIMATE' | 'PHISHING' | 'BEC_FINANCIAL' | 'CREDENTIAL_HARVESTING' | 'IMPERSONATION' | 'UNKNOWN';
  confidence: number;
  detected_language: string | null;
  urgency_score: number;
  text_summary?: string | null;
  extracted_urls: Array<{
    original_url: string;
    final_redirect_url: string | null;
    domain_age_days: number | null;
    is_suspicious_tld: boolean;
    risk_score: number;
  }>;
}

export interface LinkedCampaign {
  campaign_id: string;
  campaign_name: string;
  total_linked_emails: number;
  first_seen?: string;
  last_seen?: string;
}
```

### 3.3 Graph Data

**Endpoint:** `GET /api/v1/cases/{case_id}/graph`

```typescript
export interface NetworkGraphData {
  case_id: string;
  nodes: Array<{
    id: string;
    label: string;
    type: 'EMAIL' | 'SENDER' | 'IP' | 'DOMAIN' | 'URL' | 'ATTACHMENT_HASH' | 'CAMPAIGN' | 'THREAT_ACTOR';
    properties: Record<string, string | number | boolean | null>;
    risk_score?: number;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    relationship: 'HAS_SENDER' | 'SENT_VIA_IP' | 'RELAYED_THROUGH' | 'HAS_REPLY_TO' | 'CONTAINS_LINK' | 'HAS_ATTACHMENT' | 'LINKED_TO_CAMPAIGN' | 'BELONGS_TO';
    weight?: number;
  }>;
  campaign_summary?: LinkedCampaign | null;
}
```

---

## 4. Output Mapping: Requests Sent to Module 2

### 4.1 Upload Raw Evidence

**Endpoint:** `POST /api/v1/cases/upload`

* **Content-Type:** `multipart/form-data`
* **Fields:**
  * `files`: array of `.eml` or `.msg` files, max 10 files, max 25 MB each
  * `client_timestamp`: ISO 8601 timestamp
  * `analyst_id`: string from authenticated session or standalone mock analyst
  * `client_sha256`: optional pre-flight SHA-256 hash per file

### 4.2 Poll Case Analysis

**Endpoint:** `GET /api/v1/cases/{case_id}/analysis`

Module 1 should poll every `NEXT_PUBLIC_POLL_INTERVAL_MS` while status is `PENDING` or `PROCESSING`, then stop polling for `COMPLETED`, `DEGRADED`, or `FAILED`.

### 4.3 Load Graph Data

**Endpoint:** `GET /api/v1/cases/{case_id}/graph`

Use only after a case has reached `COMPLETED` or `DEGRADED`.

### 4.4 Export Report

**Endpoint:** `GET /api/v1/reports/{case_id}/export`

* **Query parameters:** `format=pdf|json`, `include_raw_headers=true|false`
* **PDF response:** binary blob
* **JSON response:** same evidence data as `AnalysisResult` plus chain-of-custody metadata

---

## 5. Failure Handling Contract

* Unknown JSON fields from Module 2 must be ignored.
* Missing required fields must create a Zod parse error that is converted into a visible non-blocking warning.
* Backend unavailable states must show an offline banner and keep mock-mode navigation usable.
* Canvas failures in map or graph views must be isolated to that widget.
* User-facing messages must not expose stack traces, secrets, file system paths, or raw JWT values.

---

## 6. Standalone Completion Gate

Module 1 is ready only when these pass from inside `Module-1/`:

```bash
pnpm install
pnpm type-check
pnpm lint
pnpm test
pnpm build
```
