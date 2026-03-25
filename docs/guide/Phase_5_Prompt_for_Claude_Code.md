# PHASE 5: Multi-Chart Support, Query Decomposer, Access Control & UI Improvements

Phase 4 is complete. The POC is documented and published to GitHub.
This phase adds four capabilities on top of the existing working system.

---

## What Was Added in Phase 5

### 1. Agent 1 — Query Decomposer (`agents/query_decomposer.py`)

A new first-in-pipeline agent that detects whether the user's question asks for a single
chart or multiple distinct charts, and splits multi-chart requests into focused
sub-questions.

**Function:** `decompose_query(user_question: str) -> dict`

```python
# Example output for a multi-chart request
{
    "is_multi_chart": True,
    "charts": [
        {"label": "Chart 1: Monthly Revenue Trend 2017", "question": "Show monthly revenue trend for 2017"},
        {"label": "Chart 2: Top 10 Categories 2017",     "question": "Top 10 product categories by revenue for 2017"},
        {"label": "Chart 3: Revenue by State",           "question": "Total revenue by customer state"}
    ]
}

# Example output for a single-chart request
{
    "is_multi_chart": False,
    "charts": [
        {"label": "Chart 1", "question": "What are the top 5 sellers by revenue?"}
    ]
}
```

**Detection rules used in the prompt:**
- Single metric or analysis (even with filters) → one chart
- Multiple distinct analyses connected by "and", "also", commas, or enumeration → multiple charts
- Each sub-question must be self-contained and preserve all time/filter context

**Fallback:** If Claude's response cannot be parsed as valid JSON, the agent returns
`is_multi_chart: False` with the original question unchanged. The pipeline always continues.

---

### 2. Multi-Chart Orchestration (`agents/orchestrator.py`)

New function `process_multi_query()` added alongside the existing `process_query()`:

```python
def process_multi_query(user_question: str, log_use_case: bool = True) -> dict:
    """
    1. Calls decompose_query() → gets N chart questions
    2. Calls process_query() once per chart question
    3. Returns unified multi-chart result dict
    """
```

Return structure:
```python
{
    "original_question": str,
    "is_multi_chart": bool,
    "charts": [
        {
            "label":    "Chart 1: ...",
            "question": "...",
            "result":   <dict>   # same structure as process_query() output
        },
        ...
    ]
}
```

**Agent call count for a 3-chart request:**
1 (Decomposer) + 3 × 3 (Table Recommender + SQL Generator + Viz Recommender) = 10 total agent calls.

---

### 3. Multi-Chart UI (`app/streamlit_app.py`)

Both **Quick Insights** and **Power BI Builder** pages were updated:

- The initial run now calls `process_multi_query()` instead of `process_query()`
- **Single chart:** renders exactly as before — no visible change
- **Multiple charts:** shows an info banner ("Detected N chart requests") and renders
  each chart in a separate `st.tab`

Each tab is fully independent:
- Own Table Recommendations expander (with Re-run button)
- Own Generated SQL expander (with editable SQL + Execute button on Quick Insights)
- Own chart + data table + download buttons
- Own DAX measures + Power BI Setup Guide + MCP Commands (Power BI Builder)
- Own Confidence badge (Quick Insights)

Session state keys are indexed per chart: `qa_approved_tables_0`, `qa_sql_override_1`, `pbi_dax_2`, etc.

Helper functions extracted:
- `_run_multi_query(question)` — wraps `process_multi_query()` with spinner
- `_render_qa_chart(chart_idx, result, question)` — renders one chart on Quick Insights
- `_render_pbi_chart(chart_idx, result, question)` — renders one chart on Power BI Builder

---

### 4. Password Protection (`config.py` + `app/streamlit_app.py`)

A shared-secret password gate was added to both Quick Insights and Power BI Builder.

**Config:**
```python
# config.py
APP_PASSWORD = os.getenv("APP_PASSWORD", "insights2024")
```
Change the default or set the `APP_PASSWORD` environment variable before deploying.

**UI behaviour:**
- First query in a session: user must enter the password before agents run
- Correct password → `st.session_state["auth_verified"] = True` — not asked again in the session
- Wrong password → `st.error(...)` + `st.stop()` — agents never run, no API credits consumed
- Browser session reset → password required again

**Why:** Prevents unauthorised users from exhausting the Anthropic API quota when the
Streamlit app is shared via a public URL.

---

### 5. UI Improvements (`app/streamlit_app.py`)

**Motivation cards:** A blue info card was added at the top of both Quick Insights and
Power BI Builder pages explaining the purpose and value of each page to first-time visitors.
Both cards end with the POC dataset attribution (Olist Brazilian E-Commerce).

**Architecture sidebar:** Updated from 3 agents to 5 agents:
> Agent 1 · Query Decomposer | Agent 2 · Table Recommender | Agent 3 · SQL Generator |
> Agent 4 · Viz Recommender | Agent 5 · Orchestrator · Coordinates all

**Power BI Builder placeholder text:** Updated to reflect multi-chart capability.

---

## Agent Numbering (Post Phase 5)

| # | Name | File | Role |
|---|------|------|------|
| 1 | Query Decomposer | `agents/query_decomposer.py` | Detects intent, splits multi-chart requests |
| 2 | Table Recommender | `agents/table_recommender.py` | RAG-based table selection |
| 3 | SQL Generator | `agents/sql_generator.py` | SQL generation + self-correction (3 retries) |
| 4 | Viz Recommender | `agents/viz_recommender.py` | Chart type selection + Plotly build |
| 5 | Orchestrator | `agents/orchestrator.py` | Coordinates 1–4, logs use cases |

---

## Files Changed in Phase 5

| File | Change |
|------|--------|
| `agents/query_decomposer.py` | **New** — Agent 1 |
| `agents/orchestrator.py` | Added `process_multi_query()` |
| `app/streamlit_app.py` | Multi-chart UI, password protection, motivation cards, updated sidebar |
| `config.py` | Added `APP_PASSWORD` |
| `README.md` | Updated architecture diagram, agent table, project structure, example queries |
| `docs/architecture.md` | Full update: new agent, multi-chart data flow, updated diagrams |
| `docs/enterprise-roadmap.md` | Added Decomposer to microservices, auth update, LangGraph update |
| `docs/guide/Phase_5_Prompt_for_Claude_Code.md` | **This file** |
