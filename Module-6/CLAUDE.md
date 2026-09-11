# CLAUDE.md: Module 6 Interface Contract
## Module 6: Graph Correlation, Threat Attribution, and Persistence Engine

---

## 1. Contract Purpose

This file is the memory contract for the agent building Module 6. Keep only information required to build the graph/persistence worker independently and integrate with Module 2 later.

* **Module ID:** `MOD-06`
* **Build root:** `Module-6/` (create app files directly here; do not create a nested `module-6-graph-attribution/` directory)
* **Primary role:** Consume results from Modules 3, 4, and 5, build graph entities, persist case evidence, find related campaigns, calculate final composite risk, and return graph/report metadata to Module 2
* **Consumes from:** Module 2 Celery chord callback arguments
* **Produces to:** Module 2 Celery result payload and storage side effects
* **Owns writes to:** Neo4j, PostgreSQL, and Elasticsearch
* **Never does:** Public HTTP serving, frontend rendering, raw email parsing beyond fallback metadata extraction, GeoIP enrichment, NLP inference, or Module 2 API aggregation

Before coding, read `../Architecture_and_Plan.md` and `INSTRUCTIONS.md`.

---

## 2. Required Independence

Module 6 must compile, run, and pass tests without any other module running.

* Tests must use local contract fixtures that represent Module 3, Module 4, and Module 5 outputs.
* Database clients must be wrapped behind repositories that can be mocked.
* Unit tests must pass without live Neo4j, PostgreSQL, Elasticsearch, Redis, or sibling modules.
* Integration tests may use Docker Compose, but they are not required for the compile gate.
* All writes must be idempotent so a repeated case does not duplicate nodes or records.

---

## 3. Input Mapping: Callback Arguments from Module 2

**Task name:** `tasks.module6_graph_correlation_and_persist`

**Queue:** `queue_graph_attribution`

```python
def module6_graph_correlation_and_persist(
    results: list[dict[str, object]],
    case_id: str,
) -> dict[str, object]:
    ...
```

| Argument | Type | Required | Meaning |
| --- | --- | --- | --- |
| `results` | `list[dict[str, object]]` | Yes | Celery chord results from Modules 3, 4, and 5 |
| `case_id` | `str` | Yes | Case UUID assigned by Module 2 |

Module 6 must identify each result by its fields and/or `source_module` if Module 2 adds one. Do not depend on list order only.

### 3.1 Required Fields Consumed from Module 3

| Field | Use |
| --- | --- |
| `case_id` | Case identity |
| `status` | Degraded-input detection |
| `subject` | Email node and report metadata |
| `timestamp` | Email node timeline |
| `hashes.sha256`, `hashes.md5` | Evidence identity |
| `attachment_hashes` | Attachment nodes |
| `sender_alignment.header_from` | Sender and domain nodes |
| `sender_alignment.reply_to` | Reply-to sender node |
| `raw_hop_chain` | Relay IP relationships |
| `raw_headers` | Elasticsearch full-text index |
| `header_anomaly_score` | Composite score input |

### 3.2 Required Fields Consumed from Module 4

| Field | Use |
| --- | --- |
| `case_id` | Case identity |
| `status` | Degraded-input detection |
| `geo_risk_score` | Composite score input |
| `earliest_reliable_ip` | Origin IP relationship |
| `hops` | IP nodes and relay relationships |
| `domain_intel` | Domain node properties and typosquat flags |

### 3.3 Required Fields Consumed from Module 5

| Field | Use |
| --- | --- |
| `case_id` | Case identity |
| `status` | Degraded-input detection |
| `content_suspicion_score` | Composite score input |
| `classification`, `confidence`, `urgency_score` | Case metadata and scoring rationale |
| `text_summary` | Report metadata and Elasticsearch index |
| `extracted_urls` | URL nodes and relationships |

---

## 4. Output Mapping: Result Returned to Module 2

Return this shape after graph correlation and persistence.

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
  "graph_projection": {
    "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
    "nodes": [
      {
        "id": "email_case_550e8400",
        "label": "Urgent Wire Transfer Request",
        "type": "EMAIL",
        "properties": {
          "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "threat_level": "CRITICAL"
        },
        "risk_score": 88.75
      }
    ],
    "edges": [],
    "campaign_summary": {
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

### 4.1 Field Rules

| Field | Rule |
| --- | --- |
| `status` | `SUCCESS`, `DEGRADED`, or `FAILED` |
| `composite_score` | Float from `0.0` to `100.0`, clamped |
| `threat_level` | `CLEAN`, `SUSPICIOUS`, `HIGH_RISK`, or `CRITICAL` |
| `graph_reputation_score` | Float from `0.0` to `100.0`, clamped |
| `linked_campaign` | `null` when no campaign is linked |
| `graph_projection` | Module 1 compatible graph payload for Module 2 to proxy or cache |
| `persistence_status` | Boolean status for each owned persistence target |

### 4.2 Failure Shape

If a non-critical persistence target fails, return `DEGRADED` and preserve successful writes.

```json
{
  "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
  "status": "DEGRADED",
  "composite_score": 70.0,
  "threat_level": "HIGH_RISK",
  "graph_reputation_score": 0.0,
  "linked_campaign": null,
  "nodes_created": 0,
  "relationships_created": 0,
  "graph_projection": {
    "case_id": "case_550e8400-e29b-41d4-a716-446655440000",
    "nodes": [],
    "edges": [],
    "campaign_summary": null
  },
  "persistence_status": {
    "postgres_saved": true,
    "elasticsearch_indexed": false,
    "neo4j_synced": false
  },
  "error": {
    "code": "PARTIAL_PERSISTENCE_FAILURE",
    "message": "One or more persistence targets were unavailable.",
    "recoverable": true
  }
}
```

Use `FAILED` only when no valid case identity exists or all required input payloads are unusable.

---

## 5. Graph Contract

Required node labels:

```text
Email, Sender, Domain, IPAddress, URL, Attachment, Campaign, ThreatActor
```

Required relationship types:

```text
HAS_SENDER, BELONGS_TO, SENT_VIA_IP, RELAYED_THROUGH, HAS_REPLY_TO, CONTAINS_LINK, HAS_ATTACHMENT, LINKED_TO_CAMPAIGN, ATTRIBUTED_TO
```

All Cypher writes must use `MERGE`, not `CREATE`.

When building `graph_projection`, map internal graph labels to Module 1 node types:

| Internal label | Projection type |
| --- | --- |
| `Email` | `EMAIL` |
| `Sender` | `SENDER` |
| `Domain` | `DOMAIN` |
| `IPAddress` | `IP` |
| `URL` | `URL` |
| `Attachment` | `ATTACHMENT_HASH` |
| `Campaign` | `CAMPAIGN` |
| `ThreatActor` | `THREAT_ACTOR` |

---

## 6. Scoring Contract

```text
composite_score =
  header_anomaly_score * 0.25 +
  geo_risk_score * 0.25 +
  content_suspicion_score * 0.30 +
  graph_reputation_score * 0.20
```

Threat levels:

| Score range | Threat level |
| --- | --- |
| `0.0 - 29.9` | `CLEAN` |
| `30.0 - 59.9` | `SUSPICIOUS` |
| `60.0 - 84.9` | `HIGH_RISK` |
| `85.0 - 100.0` | `CRITICAL` |

---

## 7. Standalone Completion Gate

Module 6 is ready only when these pass from inside `Module-6/`:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
pytest tests/ -v --cov=app
python -c "from app.core.celery_app import celery_app; print(celery_app.main)"
```

The test suite must pass with mocked repositories and no sibling modules running.
