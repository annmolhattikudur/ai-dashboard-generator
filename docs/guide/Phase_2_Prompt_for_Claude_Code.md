# PHASE 2: Build the AI Agents and Orchestrator (Steps 4-7)

Phase 1 is complete. The database is loaded, metadata is generated and enriched.
Now build the intelligence layer — the three AI agents and the orchestrator that 
coordinates them.

The metadata files are in the metadata/ folder. The SQLite database is at 
database/fmcg_warehouse.db. Use these existing files — do not regenerate them.

All Claude API calls must use:
- Anthropic Python SDK
- Model: claude-sonnet-4-20250514
- API key from environment variable: ANTHROPIC_API_KEY
- Proper error handling and timeout settings
- Type hints and docstrings on all functions

---

### STEP 4: Agent — Table Recommender (agents/table_recommender.py)

Build a function `recommend_tables(user_question: str) -> dict` that:

1. Loads all metadata files (table_registry, data_dictionary, relationships, 
   use_case_log) AND the domain_knowledge.json file
2. Constructs a SYSTEM PROMPT for Claude that includes:
   - All table metadata as context (this is the RAG part)
   - The domain knowledge with metric definitions and SQL patterns
   - The relationships between tables
   - Any previous use cases from the feedback log that are similar
   - Instructions to recommend which tables are needed, explain WHY each table 
     is needed, and suggest JOIN conditions
3. Sends the user's question + system prompt to Claude API (claude-sonnet-4-20250514)
4. Returns a structured response:
```python
{
    "recommended_tables": ["table1", "table2"],
    "reasoning": "You need table1 for revenue data and table2 for product names...",
    "suggested_joins": [
        {"left": "table1.product_id", "right": "table2.product_id", "type": "INNER JOIN"}
    ],
    "relevant_columns": {
        "table1": ["revenue", "quantity", "order_date"],
        "table2": ["product_name", "category"]
    },
    "similar_past_use_cases": []
}
```

Use the Anthropic Python SDK. The API key should come from an environment variable 
ANTHROPIC_API_KEY.

---

### STEP 5: Agent — SQL Generator (agents/sql_generator.py)

Build a function `generate_and_run_sql(user_question: str, table_recommendations: dict) -> dict` that:

1. Takes the user's natural language question and the table recommender's output
2. Constructs a system prompt with:
   - The recommended tables' full metadata (column types, sample values)
   - The domain knowledge (metric definitions, SQL patterns, business rules)
   - The join conditions
   - Instructions to write SQLite-compatible SQL
   - Instructions to include comments in the SQL explaining each part
3. Sends to Claude API to generate SQL
4. VALIDATES the SQL: 
   - Parse it to check for syntax errors
   - Verify all referenced tables and columns exist in the database
   - If invalid, send the error back to Claude for self-correction (max 3 retries)
5. EXECUTES the SQL against SQLite
6. Returns:
```python
{
    "sql_query": "SELECT ...",
    "sql_explanation": "This query joins sales with products to...",
    "results": pandas.DataFrame,
    "row_count": 150,
    "column_names": ["product_name", "total_revenue", "region"],
    "execution_time_ms": 45,
    "errors": []
}
```

IMPORTANT: Add safety checks — the generated SQL should NEVER contain DROP, DELETE, 
UPDATE, INSERT, ALTER, or CREATE statements. Read-only queries only.

---

### STEP 6: Agent — Visualization Recommender (agents/viz_recommender.py)

Build a function `recommend_visualization(user_question: str, query_results: dict) -> dict` that:

1. Takes the user question and the SQL results
2. Analyzes the result shape (number of rows, columns, data types)
3. Sends to Claude API with instructions to recommend:
   - The best chart type (bar, line, pie, scatter, heatmap, table, KPI card)
   - Which columns go on which axis
   - Any grouping, coloring, or filtering suggestions
   - A title for the chart
4. Returns:
```python
{
    "chart_type": "bar",
    "x_axis": "product_name",
    "y_axis": "total_revenue",
    "color_by": "region",
    "title": "Top Products by Revenue Across Regions",
    "plotly_config": { ... },
    "powerbi_suggestion": "Use a clustered bar chart with product_name on axis, 
                           total_revenue as values, region as legend"
}
```

Also generate the actual Plotly figure code so Streamlit can render it directly.

---

### STEP 7: Orchestrator (agents/orchestrator.py)

Build the master orchestrator function `process_query(user_question: str) -> dict` that:

1. Calls table_recommender → gets table recommendations
2. Shows recommendations to user (via return value) and allows them to 
   accept/modify before proceeding
3. Calls sql_generator → generates and runs SQL
4. Calls viz_recommender → gets visualization recommendation
5. Returns everything packaged together:
```python
{
    "user_question": "...",
    "table_recommendations": { ... },
    "sql_results": { ... },
    "visualization": { ... },
    "timestamp": "..."
}
```

Include error handling at each step with clear error messages.

---

## END OF PHASE 2

After building everything above:
1. Test the orchestrator with this command:
   python -c "from agents.orchestrator import process_query; import json; result = process_query('What are the top 5 product categories by total revenue?'); print(json.dumps({k: str(v)[:200] for k, v in result.items()}, indent=2))"
2. If it works, make a git commit: "feat: intelligence layer - all agents and orchestrator"
3. STOP and show me the test results before proceeding to Phase 3 (frontend)
