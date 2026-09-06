# INSTRUCTIONS.md: AI Agent Designing & Coding Standards
## Module 6: Graph Correlation, Threat Attribution & Persistence Engine

---

## 1. Module Identity & Architectural Boundary
* **Module Name:** `module-6-graph-attribution`
* **Owner:** Member 6 (Backend Dev 4)
* **Framework Stack:** Python 3.11+, Celery, Redis, Neo4j (`neo4j` driver / Cypher), PostgreSQL (`asyncpg` / SQLAlchemy 2.0), Elasticsearch (`elasticsearch-py`), Pydantic V2.
* **Core Function:** Consumes parsed findings from Modules 3, 4, and 5 via Celery chord callback, models threat entities (`Email`, `Sender`, `Domain`, `IP`, `URL`, `AttachmentHash`) in Neo4j, executes Cypher cluster queries to discover organized attack campaigns, computes the final unified `composite_risk_score`, and persists structured evidence in PostgreSQL and Elasticsearch.
* **Isolation Guarantee:** Module 6 acts as the **SOLE** write authority for persistent storage (Neo4j, PostgreSQL, Elasticsearch). It receives input payloads strictly via Celery task execution (`queue_graph_attribution`) and **NEVER** exposes HTTP endpoints directly.

---

## 2. Directory Structure & Code Layout Guidelines

When generating or editing code for Module 6, strictly follow this repository layout:

```
module-6-graph-attribution/
├── app/
│   ├── worker.py                   # Celery worker entrypoint & chord callback task
│   ├── core/
│   │   ├── config.py               # Database URIs, credentials, and scoring weights
│   │   └── celery_app.py           # Celery application instance configured for queue_graph_attribution
│   ├── graph/
│   │   ├── node_builder.py         # Converts engine payloads into typed Neo4j graph nodes
│   │   ├── cypher_queries.py       # Parametrized Cypher query templates (MERGE, MATCH, OPTIONAL MATCH)
│   │   └── campaign_clustering.py  # Graph community detection & infrastructure link analyzer
│   ├── scoring/
│   │   └── composite_risk.py       # Weighted Risk Score matrix calculation
│   ├── persistence/
│   │   ├── postgres_repo.py        # Case metadata, audit log, and status persistence
│   │   └── es_indexer.py           # Full-text indexing for raw headers, subject, and text bodies
│   ├── schemas/
│   │   └── output_schema.py        # Strict Pydantic model for final aggregated payload
│   └── utils/
│       ├── neo4j_client.py         # Thread-safe Neo4j driver connection pool
│       ├── pg_client.py            # Async SQLAlchemy / asyncpg engine session manager
│       └── es_client.py            # Elasticsearch async client wrapper
├── tests/
│   ├── test_node_builder.py
│   ├── test_cypher_queries.py
│   ├── test_campaign_clustering.py
│   └── test_composite_risk.py
├── requirements.txt
└── Dockerfile
```

---

## 3. Designing & Coding Standards

### A. Neo4j Property Graph Model Design
1. **Node Schema Definitions:**
   * `(:Email {id: case_id, hash: sha256, timestamp: ISO8601, subject: str})` (populated from Module 3 payload)
   * `(:Sender {email: str})`
   * `(:Domain {name: str, creation_age: int, is_new: bool})`
   * `(:IPAddress {ip: str, country: str, asn: str, is_vpn: bool, is_tor: bool})`
   * `(:URL {url: str, final_url: str, risk_score: float})`
   * `(:Attachment {sha256: str, name: str})`
   * `(:Campaign {id: str, name: str, first_seen: ISO8601})`
   * `(:ThreatActor {id: str, alias: str, confidence: float})`

2. **Relationship Schema Definitions:**
   * `(:Email)-[:HAS_SENDER]->(:Sender)`
   * `(:Sender)-[:BELONGS_TO]->(:Domain)`
   * `(:Email)-[:SENT_VIA_IP]->(:IPAddress)`
   * `(:Email)-[:RELAYED_THROUGH]->(:IPAddress)`
   * `(:Email)-[:HAS_REPLY_TO]->(:Sender)`
   * `(:Email)-[:CONTAINS_LINK]->(:URL)`
   * `(:Email)-[:HAS_ATTACHMENT]->(:Attachment)`
   * `(:Email)-[:LINKED_TO_CAMPAIGN]->(:Campaign)`

3. **Cypher Idempotency Standard (CRITICAL):**
   * **ALL** Cypher write queries MUST use `MERGE` instead of `CREATE` to ensure nodes and relationships are never duplicated upon re-processing.
   * **Example Pattern:**
     ```cypher
     MERGE (e:Email {id: $case_id})
     ON CREATE SET e.hash = $sha256, e.subject = $subject, e.timestamp = $timestamp
     MERGE (s:Sender {email: $sender_email})
     MERGE (e)-[:HAS_SENDER]->(s)
     ```

### B. Campaign Clustering & Link Analysis
1. **Cluster Query Execution (Query Bounding Guardrail):**
   * Execute scoped Cypher path traversal queries (`MATCH path = (e1:Email)-[:SENT_VIA_IP|:HAS_ATTACHMENT|:CONTAINS_LINK*1..3]-(e2:Email) WHERE e1.id <> e2.id RETURN path`) to discover shared high-fidelity infrastructure without query path explosion across generic relay nodes.
   * Calculate `graph_reputation_score` (0.0 to 100.0) based on the number of historical malicious cases connected to the same infrastructure.

### C. Unified Composite Risk Score Formula
Calculate `composite_score` (0.0 to 100.0) using normalized engine weights:
$$	ext{Composite Score} = (S_{	ext{Header}} 	imes 0.25) + (S_{	ext{Geo}} 	imes 0.25) + (S_{	ext{Content}} 	imes 0.30) + (S_{	ext{Graph}} 	imes 0.20)$$

* Determine **Threat Level**:
  * `0.0 - 29.9`: `CLEAN`
  * `30.0 - 59.9`: `SUSPICIOUS`
  * `60.0 - 84.9`: `HIGH_RISK`
  * `85.0 - 100.0`: `CRITICAL`

### D. Relational & Search Storage (PostgreSQL & Elasticsearch)
1. **PostgreSQL:** Persist case state, status, execution timestamps, and structured JSON metrics.
2. **Elasticsearch:** Index raw headers, extracted body text, and sender strings into index `sih_email_forensics_v1` for instant multi-field search support.

---

## 4. Error Handling & Guardrails

1. **Database Lock & Connection Resiliency:**
   * Neo4j driver connection timeouts MUST be configured with `max_connection_lifetime=300` and `connection_timeout=5.0` seconds.
   * Wrap Neo4j and PostgreSQL queries in retry decorators (`tenacity`) to automatically retry on transient connection blips.
2. **Missing Input Fault Tolerance:**
   * If input payload from any engine worker (Mod 3, Mod 4, or Mod 5) is marked `FAILED` or missing key fields, default those score inputs to `0.0`, record an anomaly flag, and proceed with persistence.

---

## 5. Testing & Quality Requirements

1. Test coverage must include Cypher query parameter validation, composite risk score calculations, and mock driver persistence tests.
2. Run test suite:
   ```bash
   pytest tests/ -v --cov=app
   ```
