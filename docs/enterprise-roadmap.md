# Enterprise Roadmap: From POC to Production

## Current State (POC)

The POC runs locally on a single machine:
- **Data layer:** SQLite with 8 CSV tables (~1.55M rows)
- **AI layer:** Claude API calls from a Python process
- **Metadata:** JSON files on disk
- **Frontend:** Streamlit running on localhost
- **Auth:** None
- **Export:** Local file downloads + MCP prompts

This is production-quality architecture in miniature. Every component has a direct enterprise equivalent.

---

## POC → Enterprise Mapping

| POC Component | Enterprise Equivalent | Reason for Change |
|---|---|---|
| SQLite | **BigQuery** | Scale, concurrency, managed service, SQL dialect |
| CSV files in `data/raw/` | **GCS buckets + BigQuery Data Transfer** | Automated ingestion pipelines |
| JSON metadata files | **Firestore + Vertex AI Vector Search** | Real-time updates, semantic search at scale |
| Direct Claude API calls | **Vertex AI (Gemini) or Anthropic API via VPC** | Private networking, SLA, cost governance |
| Streamlit on localhost | **Cloud Run + custom React frontend** | Multi-tenant, scalable, SSO-ready |
| Local file downloads | **Power BI Service REST API** | Automated report publishing to workspaces |
| No auth | **Google Identity Platform / Azure AD SSO** | Enterprise RBAC, audit trail |
| `use_case_log.json` | **BigQuery audit table + Firestore** | Queryable at scale, real-time |
| Python process | **Cloud Run microservices** | Independent scaling per agent |
| Local MCP prompts | **Power BI Remote MCP Server** | Direct API connection to Power BI Service |

---

## Phase 1 — Cloud Data Layer

**Goal:** Move data off the analyst's machine.

### BigQuery Migration

Replace `database/fmcg_warehouse.db` (SQLite) with BigQuery:

```sql
-- Current (SQLite)
SELECT strftime('%Y-%m', order_purchase_timestamp) as month, SUM(payment_value)
FROM olist_orders_dataset o JOIN olist_order_payments_dataset p ...

-- Enterprise (BigQuery)
SELECT FORMAT_DATETIME('%Y-%m', DATETIME(order_purchase_timestamp)) as month,
       SUM(payment_value)
FROM `project.dataset.olist_orders_dataset` o
JOIN `project.dataset.olist_order_payments_dataset` p ...
```

SQL generation agent prompt needs one additional rule: "Use BigQuery SQL dialect — use DATETIME() not strftime(), use backtick-quoted table references."

### GCS + Data Transfer

```
Source data (ERP / e-commerce platform)
    ↓
GCS bucket (raw zone)
    ↓
BigQuery Data Transfer Service (scheduled)
    ↓
BigQuery dataset (processed zone)
    ↓
AI Dashboard Generator agents
```

---

## Phase 2 — Vector Database for Metadata

**Goal:** Replace JSON file RAG with true semantic search as the metadata catalogue grows.

### Current RAG (JSON)

```
User question → inject all JSON files → Claude reads everything
```

Works well up to ~20 tables. At 100+ tables, the context window fills with irrelevant metadata.

### Enterprise RAG (Vector Search)

```
User question
    ↓
Embed question (text-embedding-gecko or Anthropic embeddings)
    ↓
Search Vertex AI Vector Search for top-K relevant metadata chunks
    ↓
Inject only the relevant chunks into the prompt
    ↓
Claude generates SQL with focused, high-signal context
```

**Metadata chunks to embed:**
- Table descriptions (1 chunk per table)
- Column descriptions (1 chunk per column group)
- Metric definitions (1 chunk per metric)
- Use case log entries (1 chunk per successful Q&A pair)

**Implementation:**
- Use `google-cloud-aiplatform` SDK for Vector Search
- Store full metadata in Firestore, store embeddings + Firestore IDs in Vector Search
- At query time: retrieve top-10 chunks, fetch full records from Firestore, inject into prompt

---

## Phase 3 — Agent Microservices

**Goal:** Deploy agents as independently scalable Cloud Run services.

### Service Architecture

```
Frontend (Cloud Run)
    │
    ▼
Orchestrator Service (Cloud Run)
    │
    ├── Table Recommender Service (Cloud Run)
    ├── SQL Generator Service (Cloud Run)
    └── Viz Recommender Service (Cloud Run)
            │
            ▼
        BigQuery (analytical queries)
        Firestore (metadata reads/writes)
        Vertex AI (LLM inference)
```

**Each service:**
- Stateless, containerised Python FastAPI app
- Authentication via Google Cloud IAM service accounts
- Scales to zero when idle; auto-scales on load
- Health checks, structured logging to Cloud Logging
- Request tracing via Cloud Trace

### LangChain / LangGraph Integration

For more complex multi-step reasoning (e.g., "compare Q1 2017 vs Q1 2018 across all regions and flag outliers"), consider wrapping the agent pipeline in LangGraph:

```python
from langgraph.graph import StateGraph

graph = StateGraph(DashboardState)
graph.add_node("table_recommender", table_recommender_node)
graph.add_node("sql_generator", sql_generator_node)
graph.add_node("viz_recommender", viz_recommender_node)
graph.add_node("error_handler", error_handler_node)

graph.add_conditional_edges("sql_generator", route_on_error, {
    "success": "viz_recommender",
    "error": "error_handler",
})
```

---

## Phase 4 — Enterprise Frontend

**Goal:** Replace Streamlit with a production-grade, multi-tenant UI.

### Option A — Looker Embedded

Use Looker (Google Cloud's BI platform) as the governed layer:
- AI-generated SQL → LookML model via API
- Looker handles scheduling, caching, access control, PDF exports
- Users interact via Looker's standard interface
- "AI mode" toggle brings up the NL query bar

### Option B — Custom React + FastAPI

```
React frontend (Cloud Run or Firebase Hosting)
    │ REST / WebSocket
    ▼
FastAPI backend (Cloud Run)
    │
    ▼
Agent microservices
```

Benefits: Full design control, real-time streaming responses (SSE), custom embedding in existing enterprise portals.

### Power BI Service Integration

Instead of generating local MCP prompts, call the **Power BI REST API** to publish directly:

```python
import requests

# Publish dataset to Power BI workspace
response = requests.post(
    f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets",
    headers={"Authorization": f"Bearer {access_token}"},
    json=powerbi_dataset_schema,
)

# Push rows to the dataset
requests.post(
    f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/tables/{table_name}/rows",
    headers={"Authorization": f"Bearer {access_token}"},
    json={"rows": dataframe_to_rows(df)},
)
```

This eliminates the manual Excel download step — query results publish automatically to the analyst's Power BI workspace.

---

## Phase 5 — Production Hardening

### Authentication and RBAC

```python
# Example: Row-level security in BigQuery
CREATE ROW ACCESS POLICY sales_team_filter
ON dataset.olist_orders_dataset
GRANT TO ("group:sales@company.com")
FILTER USING (seller_state = SESSION_USER_ATTRIBUTE('region'));
```

- Use Google Identity Platform or Azure AD for SSO
- Map user groups to BigQuery row-level security policies
- Agents always query with the user's impersonated service account

### Cost Controls

```python
# Estimate query cost before execution
from google.cloud import bigquery

client = bigquery.Client()
job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
dry_run_job = client.query(sql, job_config=job_config)

bytes_processed = dry_run_job.total_bytes_processed
estimated_cost_usd = bytes_processed / 1e12 * 5.00  # $5 per TB

if estimated_cost_usd > MAX_QUERY_COST_USD:
    raise QueryCostExceededError(f"Estimated cost ${estimated_cost_usd:.2f} exceeds limit")
```

Additional controls:
- BigQuery custom quotas (bytes per day per user)
- LLM token budgets (track input/output tokens, alert at threshold)
- Query result caching (Redis) for repeated identical questions
- Scheduled queries (replace ad-hoc with pre-computed aggregates for common questions)

### Audit Logging

Every query logged to BigQuery:

```sql
CREATE TABLE audit.dashboard_queries (
    query_id        STRING,
    user_id         STRING,
    timestamp       TIMESTAMP,
    question        STRING,
    tables_used     ARRAY<STRING>,
    sql_generated   STRING,
    rows_returned   INT64,
    execution_ms    FLOAT64,
    was_helpful     BOOL,
    error_count     INT64,
    llm_input_tokens  INT64,
    llm_output_tokens INT64,
    estimated_cost_usd FLOAT64
);
```

---

## MCP Integration Roadmap

### Current (POC)

```
Path B → generate MCP prompts (.txt) → user pastes into Claude Desktop
                                      → Claude Desktop + local MCP server
                                      → Power BI Desktop (local)
```

### Near-term

```
Path B → Power BI Modeling MCP Server (remote) → Power BI Desktop (local)
         (MCP over HTTP, no copy-paste required)
```

### Long-term

```
Path B → Power BI REST API → Power BI Service (cloud)
         (fully automated, no local Power BI Desktop required)
         Reports published directly to team workspace with refresh schedule
```

### BigQuery MCP

For the data layer, the [BigQuery MCP Server](https://github.com/LucasFaudman/mcp-bigquery) allows Claude to directly query BigQuery. In a mature architecture, this replaces the custom SQL Generator agent:

```
User question
    ↓
Claude + BigQuery MCP → directly queries BigQuery
    ↓
Results → Viz Recommender → chart
```

The metadata RAG layer would still be needed to guide table selection and apply business rules before Claude generates the BigQuery SQL.

---

## Security Considerations

| Risk | Mitigation |
|---|---|
| SQL injection via NL input | Blocklist of DML keywords enforced before execution; BigQuery parameterised queries |
| Sensitive data in LLM prompts | Inject only column names/descriptions, never raw data values; use Anthropic's data retention policies |
| LLM hallucinated table names | Validate all table references against `table_registry.json` before execution |
| Excessive BigQuery costs | Dry-run cost estimation gate + per-user quotas |
| Prompt injection via data values | Sanitise sample values in metadata before injection; never inject live row data into prompts |
| Unauthorised cross-tenant data | BigQuery row-level security + per-user service account impersonation |

---

## Cost Estimation Framework (Monthly)

| Component | POC Cost | Enterprise Cost (estimate) |
|---|---|---|
| LLM (Claude API) | ~$5–20/month (dev use) | ~$200–2,000/month (1,000 daily users × 3 agent calls) |
| Data storage | $0 (local SQLite) | ~$50–200/month (BigQuery Storage) |
| Query compute | $0 (local) | ~$100–500/month (BigQuery on-demand) |
| Vector search | $0 | ~$100–300/month (Vertex AI Vector Search) |
| Cloud Run | $0 | ~$50–200/month (4 services, moderate traffic) |
| Total | **~$5–20/month** | **~$500–3,200/month** |

Cost optimisations:
- Cache frequent queries in Redis (~60% reduction in LLM costs)
- Use BigQuery flat-rate pricing at high volume
- Pre-compute common aggregates (revenue by month, top categories) as scheduled queries
