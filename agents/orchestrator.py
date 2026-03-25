"""
Master Orchestrator Agent
Coordinates the three agents (table recommender, SQL generator, viz recommender)
to process a user's natural language question end-to-end.
"""

import json
from datetime import datetime
from typing import Any

import pandas as pd

from agents.table_recommender import recommend_tables
from agents.sql_generator import generate_and_run_sql
from agents.viz_recommender import recommend_visualization
from config import USE_CASE_LOG_PATH


# ─────────────────────────────────────────────
# Use-case log helpers
# ─────────────────────────────────────────────

def _load_use_case_log() -> dict:
    try:
        with open(USE_CASE_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"use_cases": []}


def _save_use_case_log(log: dict) -> None:
    with open(USE_CASE_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def _append_use_case(
    user_question: str,
    table_recommendations: dict,
    sql_results: dict,
    was_helpful: bool | None = None,
) -> None:
    """Append a completed query to the use_case_log.json for future RAG context."""
    log = _load_use_case_log()
    use_cases = log.get("use_cases", [])
    new_id = f"uc_{len(use_cases) + 1:03d}"
    use_cases.append({
        "id": new_id,
        "user_question": user_question,
        "tables_recommended": table_recommendations.get("recommended_tables", []),
        "tables_actually_used": table_recommendations.get("recommended_tables", []),
        "sql_generated": sql_results.get("sql_query", ""),
        "sql_used": sql_results.get("sql_query", ""),
        "was_helpful": was_helpful,
        "timestamp": datetime.utcnow().isoformat(),
    })
    log["use_cases"] = use_cases
    _save_use_case_log(log)


# ─────────────────────────────────────────────
# Main orchestration function
# ─────────────────────────────────────────────

def process_query(
    user_question: str,
    override_tables: list[str] | None = None,
    log_use_case: bool = True,
) -> dict:
    """
    Process a natural language question end-to-end through all three agents.

    Args:
        user_question:   Natural language question from the user.
        override_tables: Optional list of table names to use instead of the
                         table recommender's output (for user corrections).
        log_use_case:    Whether to append this query to the use_case_log.

    Returns:
        dict with keys:
            user_question, table_recommendations, sql_results,
            visualization, timestamp, errors
    """
    timestamp = datetime.utcnow().isoformat()
    errors: list[str] = []

    # ── Step 1: Table Recommender ──────────────────────────────
    print(f"[Orchestrator] Step 1/3 — Table Recommender...")
    try:
        table_recommendations = recommend_tables(user_question)
        if override_tables:
            table_recommendations["recommended_tables"] = override_tables
            table_recommendations["reasoning"] += " (tables overridden by user)"
        print(f"  Tables: {table_recommendations.get('recommended_tables', [])}")
    except Exception as e:
        error_msg = f"Table Recommender failed: {e}"
        errors.append(error_msg)
        print(f"  ERROR: {error_msg}")
        return {
            "user_question": user_question,
            "table_recommendations": {},
            "sql_results": {},
            "visualization": {},
            "timestamp": timestamp,
            "errors": errors,
        }

    # ── Step 2: SQL Generator ──────────────────────────────────
    print(f"[Orchestrator] Step 2/3 — SQL Generator...")
    try:
        sql_results = generate_and_run_sql(user_question, table_recommendations)
        if sql_results.get("errors"):
            errors.extend(sql_results["errors"])
            print(f"  SQL errors: {sql_results['errors']}")
        else:
            print(f"  SQL OK — {sql_results.get('row_count', 0)} rows in {sql_results.get('execution_time_ms', 0)}ms")
    except Exception as e:
        error_msg = f"SQL Generator failed: {e}"
        errors.append(error_msg)
        print(f"  ERROR: {error_msg}")
        sql_results = {
            "sql_query": "",
            "sql_explanation": "",
            "results": pd.DataFrame(),
            "row_count": 0,
            "column_names": [],
            "execution_time_ms": 0,
            "errors": [error_msg],
        }

    # ── Step 3: Visualization Recommender ─────────────────────
    print(f"[Orchestrator] Step 3/3 — Visualization Recommender...")
    try:
        visualization = recommend_visualization(user_question, sql_results)
        print(f"  Chart: {visualization.get('chart_type')} — \"{visualization.get('title')}\"")
    except Exception as e:
        error_msg = f"Visualization Recommender failed: {e}"
        errors.append(error_msg)
        print(f"  ERROR: {error_msg}")
        visualization = {
            "chart_type": "table",
            "title": user_question,
            "errors": [error_msg],
        }

    # ── Log use case ───────────────────────────────────────────
    if log_use_case and not sql_results.get("errors"):
        try:
            _append_use_case(user_question, table_recommendations, sql_results)
        except Exception as e:
            print(f"  Warning: could not save use case log: {e}")

    print(f"[Orchestrator] Done — {len(errors)} error(s)")

    return {
        "user_question": user_question,
        "table_recommendations": table_recommendations,
        "sql_results": sql_results,
        "visualization": visualization,
        "timestamp": timestamp,
        "errors": errors,
    }


# ─────────────────────────────────────────────
# Multi-chart orchestration
# ─────────────────────────────────────────────

def process_multi_query(
    user_question: str,
    log_use_case: bool = True,
) -> dict:
    """
    Decompose a potentially multi-chart question and process each chart independently.

    Args:
        user_question:  Raw natural language request from the user.
        log_use_case:   Whether to log each sub-query to the use_case_log.

    Returns:
        {
            "original_question": str,
            "is_multi_chart": bool,
            "charts": [
                {
                    "label":    "Chart 1: <title>",
                    "question": "<focused question>",
                    "result":   <dict — same structure as process_query output>
                },
                ...
            ]
        }
    """
    from agents.query_decomposer import decompose_query

    print(f"[Orchestrator] Decomposing query: \"{user_question[:80]}...\"")
    decomposed = decompose_query(user_question)
    is_multi = decomposed.get("is_multi_chart", False)
    charts = decomposed.get("charts", [{"label": "Chart 1", "question": user_question}])
    print(f"  Multi-chart: {is_multi} — {len(charts)} chart(s) detected")

    results = []
    for i, chart in enumerate(charts):
        label = chart.get("label", f"Chart {i + 1}")
        question = chart.get("question", user_question)
        print(f"[Orchestrator] Processing {label}...")
        result = process_query(question, log_use_case=log_use_case)
        results.append({
            "label": label,
            "question": question,
            "result": result,
        })

    return {
        "original_question": user_question,
        "is_multi_chart": is_multi,
        "charts": results,
    }


if __name__ == "__main__":
    import sys

    q = sys.argv[1] if len(sys.argv) > 1 else "What are the top 5 product categories by total revenue?"
    result = process_query(q)

    # Print a serialisable summary (DataFrames and Figures are not JSON-serialisable)
    summary: dict[str, Any] = {}
    for k, v in result.items():
        if isinstance(v, pd.DataFrame):
            summary[k] = v.head(5).to_dict(orient="records")
        elif hasattr(v, "to_json"):  # Plotly Figure
            summary[k] = "<Plotly Figure>"
        elif isinstance(v, dict):
            inner: dict[str, Any] = {}
            for ik, iv in v.items():
                if isinstance(iv, pd.DataFrame):
                    inner[ik] = iv.head(5).to_dict(orient="records")
                elif hasattr(iv, "to_json"):
                    inner[ik] = "<Plotly Figure>"
                else:
                    inner[ik] = iv
            summary[k] = inner
        else:
            summary[k] = v

    print(json.dumps(summary, indent=2, default=str))
