# INSTRUCTIONS.md: AI Agent Designing & Coding Standards
## Module 1: Presentation Layer & Forensic Data Visualization

---

## 1. Module Identity & Architectural Boundary
* **Module Name:** `module-1-frontend`
* **Owner:** Member 1 (Frontend Lead)
* **Framework Stack:** Next.js 14+ (App Router), React 18, TypeScript (Strict Mode), TailwindCSS, Shadcn UI / Radix UI, TanStack Query v5, Zustand.
* **Visualization Engine:** Leaflet.js / React-Leaflet (GeoIP Relay Map), Cytoscape.js / Vis-Network (Threat Network Graph), Recharts (Risk Scoring Analytics).
* **Isolation Guarantee:** Module 1 is strictly a Client/Presentation container. It **NEVER** communicates directly with Backend Modules 3, 4, 5, or 6. **ALL** data ingress and egress MUST strictly flow through Module 2 (Mediator API Gateway).

---

## 2. Directory Structure & Component Layout Guidelines

When generating or editing code for Module 1, strictly follow this layout structure:

```
module-1-frontend/
├── app/
│   ├── layout.tsx                  # Dark cyber-forensic shell layout
│   ├── page.tsx                    # Ingestion dropzone & quick audit feed
│   ├── investigate/
│   │   └── [caseId]/
│   │       ├── page.tsx            # Main Incident Investigation Workbench
│   │       ├── loading.tsx         # Skeleton loader for heavy visualizations
│   │       └── error.tsx           # Fallback UI for rendering/network errors
│   ├── campaigns/
│   │   └── page.tsx            # Threat Actor & Graph Cluster Matrix
│   └── reports/
│       └── page.tsx            # Evidentiary PDF Export & Case Archive
├── components/
│   ├── ui/                         # Atomic Shadcn/Radix components (Button, Badge, Card, Dialog)
│   ├── upload/
│   │   ├── Dropzone.tsx            # Drag & drop for .eml / .msg with client-side mime validation
│   │   └── UploadProgress.tsx      # Real-time parsing phase status indicator
│   ├── forensics/
│   │   ├── RiskGaugeMatrix.tsx     # Composite score radial gauge & breakdown bars
│   │   ├── HeaderBreadcrumb.tsx    # SPF/DKIM/DMARC status pills and sender alignment card
│   │   └── HeaderRawInspector.tsx  # Syntax-highlighted raw RFC header viewer with search (consumes AnalysisResult.raw_headers)
│   ├── maps/
│   │   ├── GeoHopMap.tsx           # Dynamic leaf-map with arc connections between IP nodes
│   │   └── MapControls.tsx         # Layer toggle (VPN, Tor, Proxy filters)
│   └── graphs/
│       ├── NetworkGraph.tsx        # Cytoscape.js canvas for threat entity relationships
│       └── GraphInspector.tsx      # Slide-over sidebar showing selected node metadata
├── lib/
│   ├── api/
│   │   ├── client.ts               # Axios instance with Zod schema validation
│   │   └── endpoints.ts            # Typed API fetchers for Module 2 Mediator
│   ├── hooks/
│   │   ├── useAnalysis.ts          # TanStack Query hook for case polling/SSE
│   │   └── useGraphLayout.ts       # Layout options calculator for Cytoscape.js
│   ├── store/
│   │   └── useCaseStore.ts         # Zustand store for active case selection & UI state
│   └── utils/
│       ├── geo.ts                  # Bezier curve generators for map hop arcs
│       └── formatting.ts           # Hash trimmers, timestamp formatters, risk score colors
├── types/
│   └── api-contracts.ts            # Strict TypeScript types matching Module 2 specifications
```

---

## 3. UI/UX Design System & Cyber-Forensic Theme Rules

1. **Color Palette (Dark Cyber-Security Theme):**
   * **Background Primary:** `bg-slate-950` (`#020617`)
   * **Background Surface / Cards:** `bg-slate-900` (`#0f172a`) with `border-slate-800` (`#1e293b`)
   * **Accent Primary (Cyan/Teal):** `text-cyan-400`, `bg-cyan-500/10`, `border-cyan-500/30`
   * **Pass / Clean Indicator:** `text-emerald-400`, `bg-emerald-500/10`
   * **Warning / Anomaly Indicator:** `text-amber-400`, `bg-amber-500/10`
   * **Critical / Threat High:** `text-rose-500`, `bg-rose-500/10`, glowing neon accents
   * **Entity Specific Colors (Graph Nodes):**
     * `Email` / `Header`: `#38bdf8` (Sky Blue)
     * `IP Address`: `#f59e0b` (Amber)
     * `Domain`: `#a855f7` (Purple)
     * `Threat Actor`: `#f43f5e` (Rose/Red)
     * `Hash / Attachment`: `#10b981` (Emerald)

2. **Typography & Monospace Elements:**
   * Body Text: `font-sans` (Inter or Geist)
   * Hashes (SHA-256), IP Addresses, RFC Headers, Coordinates: **MUST** use `font-mono` (`font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas`).

3. **Dynamic SSR Handling Rules (CRITICAL):**
   * Libraries depending on browser window objects (`leaflet`, `cytoscape`, `vis-network`) **MUST** be loaded dynamically in Next.js App Router using `next/dynamic` with `{ ssr: false }`.
   * **Example Pattern:**
     ```tsx
     import dynamic from 'next/dynamic';
     const DynamicGeoHopMap = dynamic(() => import('./GeoHopMap'), {
       ssr: false,
       loading: () => <MapSkeleton />
     });
     ```

4. **Error Boundary Isolation Rules:**
   * Heavy canvas components (`GeoHopMap` and `NetworkGraph`) **MUST** be wrapped in localized `<ErrorBoundary>` components.
   * If a WebGL or Leaflet canvas context fails to initialize, the error MUST be isolated to that widget slot while keeping the rest of the Forensic Dashboard fully operational.

---

## 4. TypeScript & State Management Standards

1. **Zero `any` Policy:**
   * All API requests, component props, and event handlers MUST be strictly typed using interfaces imported from `@/types/api-contracts`.
   * Unhandled runtime objects must use `unknown` with Zod schema parsing.

2. **Zod Runtime Validation for Module 2 Ingress:**
   * Every response from Module 2 MUST pass through Zod parsing at the API fetcher layer (`lib/api/client.ts`) before reaching React state. This prevents backend schema changes from crashing the UI silently.

3. **TanStack Query (React Query) Patterns:**
   * Query Key strategy: `['cases', caseId]`, `['graph', caseId, { filter }]`, `['campaigns']`.
   * Stale Time: 30,000ms for static case logs. Polling interval: 2,000ms during `status === 'PROCESSING'`.

---

## 5. UI Component Implementations Guidelines

### A. Drag-and-Drop Ingestion Dropzone
* Supported MIME types: `.eml` (`message/rfc822`), `.msg` (`application/vnd.ms-outlook`).
* Maximum File Size: 25 MB per single upload, up to 10 files batch.
* Must compute client-side SHA-256 pre-flight hash for duplicate detection UI warning before sending to Module 2.

### B. Interactive GeoIP Hop-by-Hop Trace Map
* Render base tiles using Dark Matter tiles (e.g., CartoDB Dark Matter or Mapbox Dark).
* Plot individual relay hops with numbered markers (1 = Origin, N = Final Recipient).
* Render animated or dashed SVG Bezier curves connecting consecutive hops.
* Hovering over a hop displays tooltips containing: IP, City, Country, ISP, ASN, Hop Delay (ms), and Proxy/VPN flag status.

### C. Threat Network Visualizer
* Use Cytoscape.js with `cose` or `cola` force-directed layout algorithms.
* Provide user controls: Node search, Zoom fit, Physics toggle, Category filter checkboxes (IPs, Domains, Hashes).
* Clicking a node opens the `<GraphInspector>` drawer without closing or re-rendering the main canvas.

---

## 6. Testing & Quality Gate Requirements

1. **Unit & Component Testing:**
   * Vitest + React Testing Library for testing parser UI, risk gauges, and header syntax highlighter.
2. **Mocking Infrastructure:**
   * Mock Service Worker (MSW) handlers MUST be used in development (`NEXT_PUBLIC_ENABLE_MSW_MOCKS=true`) when Module 2 is not online locally.
3. **Linting & Type-Checking Command:**
   ```bash
   pnpm type-check && pnpm lint && pnpm test
   ```
