# Architecture: AI-Powered Natural Language Dashboard Generator

## Overview

A multi-agent RAG system that converts natural language questions into data visualizations and Power BI assets — no SQL or DAX knowledge required.

The system uses Claude (Anthropic) as the reasoning engine, JSON metadata files as the domain knowledge base, and SQLite as the analytical data store. Three specialised agents run in a sequential pipeline coordinated by an orchestrator.

---

## System Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│  FRONTEND  ·  app/streamlit_app.py                                    │
│                                                                       │
│   Sidebar Navigation                 Main Content Area               │
│   ─────────────────                  ────────────────────            │
│   ⚡ Quick Insights    ────────────▶  Question input                  │
│   📊 Power BI Builder  ────────────▶  Results + Chart                 │
│   📚 Data Catalog                    Download buttons                 │
│   🔄 Feedback & Learning             Confidence badge                 │
│   💡 Example Queries                                                  │
│                                                                       │
│   st.session_state manages all UI state across reruns                 │
└───────────────────────────────────────────┬───────────────────────────┘
                                            │ process_query(question)
                                            ▼
┌───────────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR  ·  agents/orchestrator.py                              │
│                                                                       │
│   1. Call Table Recommender → get table list                          │
│   2. Call SQL Generator     → get DataFrame                           │
│   3. Call Viz Recommender   → get Plotly figure                       │
│   4. Log use case to use_case_log.json                                │
│   5. Return unified result dict to frontend                           │
└────────┬──────────────────┬──────────────────┬────────────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
  ┌─────────────┐  ┌────────────────┐  ┌──────────────────┐
  │  AGENT 1    │  │    AGENT 2     │  │    AGENT 3       │
  │  Table      │  │  SQL Generator │  │  Viz Recommender │
  │  Recommender│  │                │  │                  │
  └──────┬──────┘  └───────┬────────┘  └────────┬─────────┘
         │                 │                    │
         ▼                 ▼                    ▼
  ┌──────────────────────────────────────────────────────────┐
  │  METADATA STORE  ·  metadata/                            │
  │                                                          │
  │  table_registry.json    → schema awareness               │
  │  data_dictionary.json   → column semantics               │
  │  relationships.json     → join paths                     │
  │  domain_knowledge.json  → business logic + growth rules  │
  │  use_case_log.json      → feedback loop memory           │
  └──────────────────────────────┬───────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  SQLite DATABASE        │
                    │  fmcg_warehouse.db      │
                    │  8 tables · 1.55M rows  │
                    └────────────────────────┘
```

---

## RAG Pattern — How Metadata Becomes Intelligence

RAG (Retrieval-Augmented Generation) is the core pattern. At query time, structured metadata is retrieved from JSON files and injected directly into Claude's system prompt. Claude never touches the raw database — it reasons over the metadata descriptions.

### What Gets Injected Per Agent

**Agent 1 — Table Recommender**

```
System prompt receives:
  - Full table_registry.json     (table names, descriptions, row counts, column lists)
  - Full data_dictionary.json    (column descriptions, types, sample values)
  - Full domain_knowledge.json   (metric definitions, business rules)
  - Full relationships.json      (join graph)

Claude reasons: "Given this question, which of the 8 tables contain the relevant data?"
Output: ranked list of tables + suggested join conditions + reasoning
```

**Agent 2 — SQL Generator**

```
System prompt receives:
  - Table schemas from SQLite PRAGMA (live, always current)
  - Suggested joins from Agent 1
  - order_status_filter_rule      (exclude canceled + unavailable)
  - business_rules array          (all 13 rules)
  - growth_calculation_rules      (monthly / YTD / YoY with CTE patterns)
  - Relevant metric sql_patterns  (only for recommended tables)

Claude reasons: "Write a SQLite SELECT query that answers this question, following all rules."
Output: SQL string (validated, self-corrected up to 3 times, then executed)
```

**Agent 3 — Viz Recommender**

```
System prompt receives:
  - DataFrame shape (column names, types, sample values, row count)
  - business_rules array
  - growth_visualization_spec     (combo chart spec for growth queries)

Claude reasons: "What chart type best answers this question given this data shape?"
Output: JSON config { chart_type, x_axis, y_axis, bar_columns, line_column, title, ... }
```

### Why This Works Without Training

The LLM already knows SQL syntax, chart design principles, and Python. RAG gives it the **domain-specific knowledge** it couldn't know in advance:
- That `customer_unique_id` is the true customer identifier, not `customer_id`
- That orders with status `canceled` or `unavailable` should be excluded from metrics
- That growth for May 2018 means comparing to May 2017 using a specific CTE pattern
- Which tables need to be joined for a "revenue by category" question

When schema changes, you update one JSON file. No retraining, no deployment, no downtime.

---

## Agent 1: Table Recommender

**File:** `agents/table_recommender.py`
**Function:** `recommend_tables(user_question: str, override_tables: list | None) -> dict`

```
Input:  Natural language question
Output: {
    "recommended_tables": ["olist_orders_dataset", "olist_order_payments_dataset"],
    "suggested_joins": [{"type": "JOIN", "left": "o.order_id", "right": "p.order_id"}],
    "relevant_columns": {"olist_orders_dataset": ["order_id", "order_status", ...]},
    "reasoning": "Revenue requires payment_value from payments joined to orders..."
}
```

**RAG context injected:** Full metadata (all 5 files).
**Claude's task:** Score tables by relevance to the question.
**Override:** The UI allows users to deselect tables and re-run — this feeds `override_tables`.

---

## Agent 2: SQL Generator

**File:** `agents/sql_generator.py`
**Function:** `generate_and_run_sql(question: str, table_recommendations: dict) -> dict`

```
Input:  Question + table recommendations from Agent 1
Output: {
    "sql_query": "WITH current_period AS (...) SELECT ...",
    "sql_explanation": "This query computes revenue for May 2018 vs May 2017...",
    "results": pd.DataFrame,
    "row_count": 1,
    "execution_time_ms": 42.3,
    "errors": []
}
```

**Self-correction loop:**
```
Generate SQL
    ↓
Validate (safety check + table existence check)
    ↓ (if errors)
Send error back to Claude: "This SQL failed: [error]. Fix it."
    ↓
Max 3 attempts, then return with errors
```

**Safety checks:** Blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `TRUNCATE`.
**Execution:** Runs directly against SQLite via `pd.read_sql_query()`.

---

## Agent 3: Viz Recommender

**File:** `agents/viz_recommender.py`
**Function:** `recommend_visualization(user_question: str, query_results: dict) -> dict`

```
Input:  Question + SQL results (DataFrame)
Output: {
    "chart_type": "combo",
    "x_axis": "category",
    "y_axis": "current_revenue",
    "bar_columns": ["prior_revenue", "current_revenue"],
    "line_column": "growth_pct",
    "title": "Sales Growth by Category — May 2018 vs May 2017",
    "figure": <go.Figure>,
    "powerbi_suggestion": "...",
    "reasoning": "..."
}
```

**Chart types supported:**

| Type | When used |
|------|-----------|
| `bar` | 1 categorical + 1 numeric |
| `line` | Time series (date + numeric) |
| `pie` | Proportions with ≤8 categories |
| `scatter` | 2 numeric columns |
| `combo` | Growth queries (prior + current bars + growth % line) |
| `kpi_card` | Single aggregate value (1×1 result) |
| `table` | Fallback for complex multi-column results |

**Combo chart rendering:**
Single-row aggregate → two bars side by side with growth % annotation above.
Multi-row dimensional → grouped bars + line on secondary Y-axis with labeled data points.

---

## Orchestrator

**File:** `agents/orchestrator.py`
**Function:** `process_query(user_question: str, override_tables: list | None, log_use_case: bool) -> dict`

Coordinates the three agents:
1. Calls `recommend_tables()` — if `override_tables` provided, passes it through
2. Calls `generate_and_run_sql()` with table recs
3. Calls `recommend_visualization()` with SQL results
4. Optionally appends the interaction to `use_case_log.json`
5. Returns a unified result dict consumed by the Streamlit frontend

---

## Feedback Loop

Every query that runs through the orchestrator can be logged to `metadata/use_case_log.json`:

```json
{
  "id": "uc_20240315_143022",
  "timestamp": "2024-03-15T14:30:22",
  "user_question": "What is the sales growth for May 2018?",
  "tables_recommended": ["olist_orders_dataset", "olist_order_payments_dataset"],
  "tables_actually_used": ["olist_orders_dataset", "olist_order_payments_dataset"],
  "sql_generated": "WITH current_period AS (...) ...",
  "sql_used": "WITH current_period AS (...) ...",
  "was_helpful": true,
  "errors": []
}
```

Analysts can visit the **Feedback & Learning** page to:
- Correct which tables were actually used
- Paste the corrected SQL they actually ran
- Mark queries as helpful or not

This growing log can be referenced in future agent prompts for few-shot learning, or mined to identify systematic failures.

---

## Power BI Export Handler

**File:** `powerbi/export_handler.py`

Functions:

| Function | Output |
|----------|--------|
| `export_to_excel_bytes(df)` | Simple Excel file of the DataFrame |
| `export_standardized_excel_bytes(df, viz)` | 2-sheet Excel: Data + ChartConfig (for Power BI import) |
| `export_to_csv_bytes(df)` | CSV bytes for download |
| `generate_dax_measures(viz, question)` | List of DAX measures generated by Claude |
| `generate_powerbi_instructions(viz)` | Step-by-step Power BI setup guide as plain text |
| `generate_mcp_commands(viz, dax, df, question)` | Structured prompts for Power BI Modeling MCP Server |

---

## Data Flow: Growth Query Example

```
User asks: "What is the sales growth by category for May 2018?"

1. TABLE RECOMMENDER
   Reads metadata → identifies:
   - olist_orders_dataset        (has order_status, order_purchase_timestamp)
   - olist_order_payments_dataset (has payment_value)
   - olist_order_items_dataset   (has product_id)
   - olist_products_dataset      (has product_category_name)

2. SQL GENERATOR
   Reads growth_calculation_rules → generates CTE pattern:
   WITH current_period AS (
       SELECT pr.product_category_name, SUM(p.payment_value) AS revenue
       FROM olist_order_payments_dataset p
       JOIN olist_orders_dataset o ON p.order_id = o.order_id
       JOIN olist_order_items_dataset i ON o.order_id = i.order_id
       JOIN olist_products_dataset pr ON i.product_id = pr.product_id
       WHERE o.order_status NOT IN ('canceled','unavailable')
       AND strftime('%Y-%m', o.order_purchase_timestamp) = '2018-05'
       GROUP BY category
   ),
   prior_period AS ( ... same for '2017-05' ... )
   SELECT c.category, c.revenue AS current_revenue,
          p.revenue AS prior_revenue,
          ROUND((c.revenue - p.revenue) / p.revenue * 100, 2) AS growth_pct
   FROM current_period c LEFT JOIN prior_period p ON c.category = p.category
   ORDER BY growth_pct DESC

   → Executes → Returns DataFrame with 70 category rows

3. VIZ RECOMMENDER
   Detects columns: [category, current_revenue, prior_revenue, growth_pct]
   Reads growth_visualization_spec → selects chart_type = "combo"
   Builds: grouped bar (prior + current, two blues) + orange line (growth %)
           on secondary Y-axis, with labeled data points

4. FRONTEND
   Renders: Plotly combo chart + data table + download buttons + confidence badge
   Logs: interaction to use_case_log.json
```

---

## Configuration

All paths, model names, and settings are in `config.py`:

```python
CLAUDE_MODEL        = "claude-sonnet-4-20250514"
DATABASE_PATH       = BASE_DIR / "database" / "fmcg_warehouse.db"
METADATA_DIR        = BASE_DIR / "metadata"
MAX_SQL_RETRIES     = 3
MAX_RESULTS_DISPLAY = 500
```

Agents never hardcode paths or model names — they always import from `config.py`.
