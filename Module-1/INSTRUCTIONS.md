# INSTRUCTIONS.md: Module 1 Agent Build Brief
## Presentation Layer and Forensic Data Visualization

---

## 1. Mission

Build the analyst-facing Next.js application for SIH 26106. The dashboard must let a user upload raw email evidence, watch case processing status, inspect authentication and routing forensics, view a threat graph, and download forensic reports.

This module must be fully buildable without Modules 2, 3, 4, 5, or 6 running. Use the interface contract in `CLAUDE.md` as the source of truth for all API shapes.

---

## 2. Architecture Boundary

* Build inside `Module-1/`.
* Do not create a nested project directory.
* Do not import code from sibling module directories.
* Do not call worker queues, databases, or direct engine services.
* All live network traffic goes through Module 2 URLs only.
* All standalone development traffic is mocked with MSW.

---

## 3. Required Stack

* Next.js 14+ App Router
* React 18
* TypeScript strict mode
* TailwindCSS
* Shadcn UI or Radix UI primitives
* TanStack Query v5
* Zustand
* Zod
* MSW
* Leaflet or React-Leaflet for hop maps
* Cytoscape.js or Vis-Network for graph visualization
* Recharts for scoring charts

---

## 4. File Layout

Create this layout directly under `Module-1/`:

```text
app/
  layout.tsx
  page.tsx
  investigate/[caseId]/page.tsx
  investigate/[caseId]/loading.tsx
  investigate/[caseId]/error.tsx
  campaigns/page.tsx
  reports/page.tsx
components/
  ui/
  upload/Dropzone.tsx
  upload/UploadProgress.tsx
  forensics/RiskGaugeMatrix.tsx
  forensics/HeaderBreadcrumb.tsx
  forensics/HeaderRawInspector.tsx
  maps/GeoHopMap.tsx
  maps/MapControls.tsx
  graphs/NetworkGraph.tsx
  graphs/GraphInspector.tsx
lib/
  api/client.ts
  api/endpoints.ts
  api/schemas.ts
  hooks/useAnalysis.ts
  hooks/useGraphLayout.ts
  mocks/browser.ts
  mocks/handlers.ts
  store/useCaseStore.ts
  utils/formatting.ts
  utils/geo.ts
types/api-contracts.ts
contracts/
  upload-accepted.sample.json
  analysis-result.sample.json
  graph-data.sample.json
tests/
```

---

## 5. Input and Output Mapping

### Inputs Consumed

| Source | Transport | Data | Local owner |
| --- | --- | --- | --- |
| Module 2 | `POST /api/v1/cases/upload` response | `UploadAccepted` | `types/api-contracts.ts`, `lib/api/schemas.ts` |
| Module 2 | `GET /api/v1/cases/{case_id}/analysis` | `AnalysisResult` | `useAnalysis.ts`, investigation page |
| Module 2 | `GET /api/v1/cases/{case_id}/graph` | `NetworkGraphData` | `NetworkGraph.tsx` |
| Module 2 | `GET /api/v1/reports/{case_id}/export` | PDF blob or JSON export | reports page |

### Outputs Produced

| Destination | Transport | Data | Required behavior |
| --- | --- | --- | --- |
| Module 2 | `POST /api/v1/cases/upload` | `.eml` and `.msg` files, `client_timestamp`, `analyst_id`, optional `client_sha256` | Reject unsupported files before upload |
| Module 2 | `GET /api/v1/cases/{case_id}/analysis` | `case_id` path parameter | Poll while pending or processing |
| Module 2 | `GET /api/v1/cases/{case_id}/graph` | `case_id` path parameter | Load after completed or degraded |
| Module 2 | `GET /api/v1/reports/{case_id}/export` | `format`, `include_raw_headers` query parameters | Download without page refresh |

---

## 6. Implementation Requirements

1. Define all TypeScript interfaces and matching Zod schemas before writing UI components.
2. Build the API client so every response is parsed with Zod `safeParse`.
3. Add MSW handlers that return realistic contract fixtures for upload, polling, graph, and report flows.
4. Build the upload flow with client-side extension, size, batch count, and optional SHA-256 checks.
5. Build the investigation workbench with separate resilient panels for risk, protocol, route map, raw headers, content findings, and graph.
6. Dynamically import Leaflet/Cytoscape components with `ssr: false`.
7. Persist only UI preferences under local storage key `sih_mod1_state_v1`.
8. Keep user-facing errors sanitized and non-blocking when possible.

---

## 7. Design Requirements

* Use a dense analyst workbench, not a marketing landing page.
* Prioritize readable forensic evidence: hashes, headers, IPs, timestamps, scores, and graph relationships.
* Use monospace text for hashes, IP addresses, coordinates, and RFC headers.
* Use compact cards only for repeated case summaries or widgets.
* Keep map and graph canvases stable with fixed responsive dimensions.
* The UI must remain useful when one analysis section is degraded or missing.

---

## 8. Testing Requirements

Write tests for:

* Zod schema acceptance and rejection
* Upload validation rules
* Polling stop conditions for `COMPLETED`, `DEGRADED`, and `FAILED`
* Offline MSW mode
* Rendering of missing optional fields
* Graph and map error boundary fallback states

---

## 9. Environment Variables

```bash
NEXT_PUBLIC_MEDIATOR_API_URL="http://localhost:8000"
NEXT_PUBLIC_MEDIATOR_WS_URL="ws://localhost:8000/ws"
NEXT_PUBLIC_ENABLE_MSW_MOCKS="true"
NEXT_PUBLIC_MAX_BATCH_UPLOAD="10"
NEXT_PUBLIC_MAX_FILE_SIZE_BYTES="26214400"
NEXT_PUBLIC_POLL_INTERVAL_MS="2000"
NEXT_PUBLIC_MAPBOX_TOKEN=""
```

Do not commit real API tokens.

---

## 10. Independent Compile Gate

Run these commands from `Module-1/` before handing off:

```bash
pnpm install
pnpm type-check
pnpm lint
pnpm test
pnpm build
```

The build is not complete until it passes with MSW enabled and no backend modules running.
