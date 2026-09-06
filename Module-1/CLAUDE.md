# CLAUDE.md: Synced Memory & Module Isolation Interface Contract
## Module 1: Presentation Layer & Forensic Data Visualization

---

## 1. Module Overview & Memory Context
* **Module ID:** `MOD-01`
* **Purpose:** Frontend Web Dashboard, User Interface, Interactive Map Visualizations, Threat Graph Canvas, and Forensic PDF Report Trigger.
* **Current Version:** `1.0.0-prod`
* **Owner:** Member 1 (Frontend Lead)
* **Downstream Integration Target:** Module 2 (Mediator API Gateway)

---

## 2. Ingress Interface Schema (Inputs from Module 2 Gateway)

Module 1 expects Module 2 (Mediator) to provide the following REST API endpoints and payload schemas.

### A. Endpoint: `GET /api/v1/cases/{case_id}/analysis`
**Response Payload Contract (`AnalysisResult`):**
```typescript
export interface AnalysisResult {
  case_id: string;
  file_name: string;
  sha256_hash: string;
  md5_hash?: string;
  timestamp: string; // ISO 8601
  subject?: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  processing_time_ms: number;
  raw_headers?: string; // Full raw RFC 822 headers for inspector viewer
  
  // Composite Risk Metrics
  risk_matrix: {
    composite_score: number; // 0 - 100
    threat_level: 'CLEAN' | 'SUSPICIOUS' | 'HIGH_RISK' | 'CRITICAL';
    breakdown: {
      header_anomaly_score: number; // 0 - 100
      content_suspicion_score: number; // 0 - 100
      geo_risk_score: number; // 0 - 100
      graph_reputation_score: number; // 0 - 100
    };
    flags: Array<{
      code: string;
      severity: 'INFO' | 'WARNING' | 'CRITICAL';
      message: string;
      source_module: 'HEADER' | 'GEOIP' | 'NLP' | 'GRAPH';
    }>;
  };

  // Header & Protocol Authentication (From Module 3 via Mediator)
  protocol_forensics: {
    spf: { status: 'PASS' | 'FAIL' | 'SOFTFAIL' | 'NEUTRAL' | 'NONE' | 'TEMPERROR' | 'PERMERROR'; domain: string; ip: string };
    dkim: { status: 'PASS' | 'FAIL' | 'NONE'; selector: string; domain: string };
    dmarc: { status: 'PASS' | 'FAIL' | 'NONE'; policy: 'reject' | 'quarantine' | 'none'; alignment: boolean };
    sender_alignment: {
      header_from: string;
      envelope_from: string;
      reply_to: string | null;
      is_display_name_spoofed: boolean;
      spoofed_entity_detected: string | null;
    };
  };

  // GeoIP Hop Chain & Domain Intel (From Module 4 via Mediator)
  routing_topology: {
    total_hops: number;
    earliest_reliable_ip: string;
    origin_country: string;
    origin_city: string;
    hops: Array<{
      hop_index: number;
      ip: string;
      hostname: string | null;
      country: string;
      city: string;
      latitude: number;
      longitude: number;
      isp: string;
      asn: string;
      is_vpn_or_proxy: boolean;
      is_tor_exit_node: boolean;
      delay_from_prev_ms: number | null;
    }>;
    domain_intel?: {
      domain: string;
      domain_age_days: number | null;
      registrar: string | null;
      is_newly_registered: boolean;
      is_typosquatted: boolean;
      target_brand_spoofed: string | null;
    };
  };

  // NLP Content Assessment (From Module 5 via Mediator)
  content_analysis: {
    classification: 'LEGITIMATE' | 'PHISHING' | 'BEC_FINANCIAL' | 'CREDENTIAL_HARVESTING' | 'IMPERSONATION';
    confidence: number; // 0.0 to 1.0
    detected_language: string;
    urgency_score: number; // 0 - 100
    text_summary?: string;
    extracted_urls: Array<{
      original_url: string;
      final_redirect_url: string;
      domain_age_days: number | null;
      is_suspicious_tld: boolean;
      risk_score: number;
    }>;
  };
}
```

---

### B. Endpoint: `GET /api/v1/cases/{case_id}/graph`
**Response Payload Contract (`NetworkGraphData`):**
```typescript
export interface NetworkGraphData {
  case_id: string;
  nodes: Array<{
    id: string;
    label: string;
    type: 'EMAIL' | 'SENDER' | 'IP' | 'DOMAIN' | 'ATTACHMENT_HASH' | 'CAMPAIGN' | 'THREAT_ACTOR';
    properties: Record<string, string | number | boolean>;
    risk_score?: number;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    relationship: 'HAS_SENDER' | 'SENT_VIA_IP' | 'RELAYED_THROUGH' | 'HAS_REPLY_TO' | 'CONTAINS_LINK' | 'HAS_ATTACHMENT' | 'LINKED_TO_CAMPAIGN' | 'BELONGS_TO';
    weight?: number;
  }>;
  campaign_summary?: {
    campaign_id: string;
    campaign_name: string;
    total_linked_emails: number;
    first_seen: string;
    last_seen: string;
  };
}
```

---

## 3. Egress Interface Schema (Outputs from Module 1 to Module 2)

Module 1 sends requests to Module 2 in these exact formats:

### A. Endpoint: `POST /api/v1/cases/upload`
* **Content-Type:** `multipart/form-data`
* **Payload Fields:**
  * `files`: Binary stream array (`.eml` / `.msg`)
  * `client_timestamp`: ISO 8601 string
  * `analyst_id`: string (from JWT session)

### B. Endpoint: `GET /api/v1/reports/{case_id}/export`
* **Query Parameters:** `format=pdf|json&include_raw_headers=true`
* **Response:** Binary Blob (PDF file) or JSON payload for downloading.

---

## 4. Local Environment Variables (`.env.local`)

```bash
# Gateway Endpoint (Module 2)
NEXT_PUBLIC_MEDIATOR_API_URL="http://localhost:8000"
NEXT_PUBLIC_MEDIATOR_WS_URL="ws://localhost:8000/ws"

# Map Tile Authorization
NEXT_PUBLIC_MAPBOX_TOKEN="pk.sample_token_for_forensic_map"

# MSW Mocking Trigger (Set to true when running standalone without Module 2 backend)
NEXT_PUBLIC_ENABLE_MSW_MOCKS="false"

# UI Configuration
NEXT_PUBLIC_MAX_BATCH_UPLOAD="10"
NEXT_PUBLIC_POLL_INTERVAL_MS="2000"
```

---

## 5. Isolated Running & Testing Commands

To run and verify Module 1 in total isolation on any machine:

```bash
# 1. Install Dependencies
pnpm install

# 2. Run Standalone Development Server with MSW Mock Data
pnpm dev:mock

# 3. Type Checking & Code Formatting
pnpm type-check
pnpm lint

# 4. Run Vitest Unit Tests
pnpm test:unit

# 5. Production Build Verification
pnpm build
pnpm start
```

---

## 6. Zero-Coupling Cross-Module Fault Isolation Rules

1. **Schema Drift Guardrail:**
   * If Module 2 returns unexpected JSON fields or missing keys, Module 1 **MUST NOT** throw unhandled React render exceptions.
   * All API calls must route through Zod safe-parsing wrappers in `@/lib/api/client.ts`. If parsing fails, fall back to a gracefully degraded UI state with a non-blocking toast warning (`"Data field warning from Gateway"`).

2. **Backend Unavailability Resilience:**
   * If Module 2 is down (HTTP 502/503/Connection Refused), Module 1 renders a persistent offline status bar at the top of the workbench, offering an **"Enable Offline Mock Mode"** button so analysts/judges can still evaluate UI features using MSW local snapshots.

3. **Memory & Storage Boundaries:**
   * All local state persistence (active view tab, graph node selections, map layer toggles) is scoped strictly under local storage key `sih_mod1_state_v1`.
