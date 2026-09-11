# INSTRUCTIONS.md: Module 6 Agent Build Brief
## Graph Correlation, Threat Attribution, and Persistence Engine

---

## 1. Mission

Build the Celery callback worker that turns engine results into persistent forensic intelligence for SIH 26106. Module 6 consumes validated outputs from Modules 3, 4, and 5 through Module 2, writes graph and evidence records, links related campaigns, computes final composite risk, and returns a typed result to Module 2.

This module must be fully buildable without Modules 1, 2, 3, 4, or 5 running. Use `CLAUDE.md` as the source of truth for the task signature and result payload.

---

## 2. Architecture Boundary

* Build inside `Module-6/`.
* Do not create a nested project directory.
* Do not import code from sibling module directories.
* Do not expose HTTP endpoints.
* Own all writes to Neo4j, PostgreSQL, and Elasticsearch.
* Do not perform header parsing, GeoIP enrichment, URL redirect analysis, or NLP inference.
* Tests must mock repositories so unit tests run without live databases.

---

## 3. Required Stack

* Python 3.11+
* Celery
* Redis
* Pydantic V2
* Neo4j Python driver
* SQLAlchemy 2.0 or `asyncpg`
* Elasticsearch Python client
* Tenacity
* Pytest

---

## 4. File Layout

Create this layout directly under `Module-6/`:

```text
app/
  worker.py
  core/config.py
  core/celery_app.py
  graph/node_builder.py
  graph/cypher_queries.py
  graph/campaign_clustering.py
  scoring/composite_risk.py
  persistence/postgres_repo.py
  persistence/es_indexer.py
  persistence/graph_repo.py
  schemas/input_schema.py
  schemas/output_schema.py
  utils/neo4j_client.py
  utils/pg_client.py
  utils/es_client.py
contracts/
  module3-header-result.sample.json
  module4-geoip-result.sample.json
  module5-nlp-result.sample.json
  module6-graph-result.sample.json
tests/
  test_input_schema.py
  test_node_builder.py
  test_cypher_queries.py
  test_campaign_clustering.py
  test_composite_risk.py
  test_persistence_repos.py
  test_worker_task.py
requirements.txt
Dockerfile
docker-compose.yml
```

`docker-compose.yml` may start Redis, Neo4j, PostgreSQL, and Elasticsearch for optional integration testing. Unit tests must pass without it.

---

## 5. Input and Output Mapping

### Inputs Consumed

| Source | Transport | Data | Local owner |
| --- | --- | --- | --- |
| Module 2 | Celery callback `tasks.module6_graph_correlation_and_persist` | `results`, `case_id` | `app/worker.py` |
| Module 3 fixture/result | Serialized dict | Header scores, sender, hashes, attachments, hop chain, raw headers | `schemas/input_schema.py` |
| Module 4 fixture/result | Serialized dict | Geo score, hop metadata, domain intel | `schemas/input_schema.py` |
| Module 5 fixture/result | Serialized dict | Content score, classification, summary, URLs | `schemas/input_schema.py` |

### Outputs Produced

| Destination | Transport | Data | Required behavior |
| --- | --- | --- | --- |
| Module 2 | Celery result | Module 6 payload from `CLAUDE.md` | Always Pydantic-validated |
| Module 2 | Celery result | `graph_projection` | Compatible with Module 1 `NetworkGraphData` |
| Neo4j | Driver writes | nodes and relationships | Idempotent `MERGE` only |
| PostgreSQL | Repository writes | case metadata, score, audit trail | Transactional and retryable |
| Elasticsearch | Index writes | raw headers, text summary, sender, subject | Failure must degrade, not crash completed DB writes |

---

## 6. Implementation Requirements

1. Validate every input payload with Pydantic before graph or score logic runs.
2. Accept `FAILED` or `DEGRADED` upstream results and continue with default score `0.0` for that input.
3. Build normalized entities for Email, Sender, Domain, IPAddress, URL, Attachment, Campaign, and ThreatActor.
4. Use parameterized Cypher query builders only.
5. Use `MERGE` for every node and relationship write.
6. Bound campaign-clustering traversals to depth 1 through 3 and high-fidelity relationships only.
7. Compute `graph_reputation_score` from historical matches on IPs, URLs, attachments, domains, and campaigns.
8. Compute and clamp `composite_score` with the formula in `CLAUDE.md`.
9. Persist PostgreSQL metadata and audit trail in one transaction.
10. Treat Elasticsearch indexing failure as `DEGRADED`, not `FAILED`, when PostgreSQL and graph writes succeed.
11. Return `graph_projection` so Module 2 can serve graph data without knowing Neo4j internals.
12. Sanitize error output.

---

## 7. Graph Model Requirements

Use these Neo4j labels:

```text
Email, Sender, Domain, IPAddress, URL, Attachment, Campaign, ThreatActor
```

Use these relationships:

```text
HAS_SENDER, BELONGS_TO, SENT_VIA_IP, RELAYED_THROUGH, HAS_REPLY_TO, CONTAINS_LINK, HAS_ATTACHMENT, LINKED_TO_CAMPAIGN, ATTRIBUTED_TO
```

Never write unbounded graph traversal queries. Never interpolate raw strings into Cypher.

Map internal graph labels to frontend projection types as follows: `Email -> EMAIL`, `Sender -> SENDER`, `Domain -> DOMAIN`, `IPAddress -> IP`, `URL -> URL`, `Attachment -> ATTACHMENT_HASH`, `Campaign -> CAMPAIGN`, `ThreatActor -> THREAT_ACTOR`.

---

## 8. Testing Requirements

Write tests for:

* Pydantic validation of Module 3, 4, and 5 fixture inputs
* Missing or failed upstream input fallback
* Node and relationship construction
* Cypher query parameterization and `MERGE` usage
* Campaign clustering depth bounds
* Composite risk score thresholds
* Partial persistence failure handling
* `graph_projection` compatibility with Module 1 graph contract
* Worker task success, degraded, and failed outputs

---

## 9. Environment Variables

```bash
REDIS_URL="redis://localhost:6379/0"
CELERY_BROKER_URL="redis://localhost:6379/0"
CELERY_RESULT_BACKEND="redis://localhost:6379/1"
CELERY_TASK_ALWAYS_EAGER="false"
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password"
NEO4J_MAX_POOL_SIZE="50"
POSTGRES_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/sih_forensics"
ELASTICSEARCH_URL="http://localhost:9200"
ES_INDEX_NAME="sih_email_forensics_v1"
EVIDENCE_STAGING_DIR="/tmp/sih_evidence_staging"
```

Do not commit production secrets.

---

## 10. Independent Compile Gate

Run these commands from `Module-6/` before handing off:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
pytest tests/ -v --cov=app
python -c "from app.core.celery_app import celery_app; print(celery_app.main)"
```

The test suite must pass with mocked repositories and no sibling modules running. Optional integration verification may run `docker-compose up -d redis neo4j postgres elasticsearch` before database-backed tests.
