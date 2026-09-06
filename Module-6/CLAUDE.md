# CLAUDE.md: Synced Memory & Module Isolation Interface Contract
## Module 6: Graph Correlation, Threat Attribution & Persistence Engine

---

## 1. Module Overview & Memory Context
* **Module ID:** `MOD-06`
* **Purpose:** Entity Extraction, Neo4j Graph Topology Construction, Attack Campaign Clustering, Composite Risk Score Calculation, PostgreSQL Audit Logging, Elasticsearch Full-Text Indexing.
* **Current Version:** `1.0.0-prod`
* **Owner:** Member 6 (Backend Dev 4)
* **Ingress Queue:** `queue_graph_attribution`
* **Orchestrator Target:** Module 2 (Mediator Celery Chord Callback)

---

## 2. Ingress Interface Schema (Task Arguments from Module 2)

Module 6 listens on Celery signature `tasks.module6_graph_correlation_and_persist`.

**Task Parameter Signature (Chord Callback):**
```python
def module6_graph_correlation_and_persist(results: list[dict[str, Any]], case_id: str) -> dict[str, Any]:
    ...
```

* `results`: List of dictionary payloads returned from upstream parallel tasks (`Module 3`, `Module 4`, `Module 5`).
* `case_id`: UUID string identifying the investigation case.

---

## 3. Egress Interface Schema (Return Payload to Module 2)

Module 6 MUST return a dictionary adhering to this exact JSON schema upon task completion:

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "composite_score": 88.75,
  "threat_level": "CRITICAL",
  "graph_reputation_score": 88.0,
  "linked_campaign": {
    "campaign_id": "cmp_991823",
    "campaign_name": "Operation Fake Invoice Alpha",
    "total_linked_emails": 42,
    "first_seen": "2026-08-15T10:00:00Z",
    "last_seen": "2026-09-06T18:00:00Z"
  },
  "nodes_created": 12,
  "relationships_created": 15,
  "graph_metrics": {
    "graph_reputation_score": 88.0,
    "nodes_created": 12,
    "relationships_created": 15,
    "linked_campaign": {
      "campaign_id": "cmp_991823",
      "campaign_name": "Operation Fake Invoice Alpha",
      "total_linked_emails": 42,
      "first_seen": "2026-08-15T10:00:00Z",
      "last_seen": "2026-09-06T18:00:00Z"
    }
  },
  "persistence_status": {
    "postgres_saved": true,
    "elasticsearch_indexed": true,
    "neo4j_synced": true
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

# Neo4j Graph Database
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password"
NEO4J_MAX_POOL_SIZE=50

# PostgreSQL
POSTGRES_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/sih_forensics"

# Elasticsearch
ELASTICSEARCH_URL="http://localhost:9200"
ES_INDEX_NAME="sih_email_forensics_v1"

# Staging Storage
EVIDENCE_STAGING_DIR="/tmp/sih_evidence_staging"
```

---

## 5. Isolated Running & Testing Commands

To run and verify Module 6 in total isolation:

```bash
# 1. Start Support Infrastructure (Redis, Neo4j, Postgres, ES) via Docker
docker-compose up -d redis neo4j postgres elasticsearch

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Start Module 6 Celery Worker
celery -A app.core.celery_app worker --loglevel=info -Q queue_graph_attribution

# 4. Run Pytest Suite
pytest tests/ -v
```

---

## 6. Zero-Coupling Cross-Module Fault Isolation Rules

1. **Exclusive Persistence Owner:** Modules 1, 2, 3, 4, and 5 DO NOT write directly to Neo4j, PostgreSQL, or Elasticsearch. Module 6 holds sole write responsibility to ensure database write locks and transaction integrity are maintained.
2. **Idempotent Graph Insertion:** Every Cypher write statement MUST use `MERGE` clauses so re-running an email case does not create duplicate nodes or corrupt network relationships.
3. **Database Fallback Resilience:** If Elasticsearch is unavailable, Module 6 logs an index warning, continues with PostgreSQL and Neo4j commits, and reports `elasticsearch_indexed: false` without crashing the pipeline.
