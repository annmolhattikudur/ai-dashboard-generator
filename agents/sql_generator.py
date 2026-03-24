"""
Agent 2: SQL Generator
Takes a user question and table recommendations, generates SQLite-compatible
SQL via Claude, validates it, self-corrects on error (max 3 retries),
and executes it against the database.
"""

import json
import re
import sqlite3
import time
from typing import Any

import anthropic
import pandas as pd

from config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    DATABASE_PATH,
    DATA_DICTIONARY_PATH,
    DOMAIN_KNOWLEDGE_PATH,
)

# DML/DDL keywords that are forbidden in generated SQL
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|REPLACE|MERGE)\b",
    re.IGNORECASE,
)

MAX_RETRIES = 3


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _load_json(path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_table_schemas(conn: sqlite3.Connection, tables: list[str]) -> dict:
    """Return column info for each requested table from the live database."""
    schemas = {}
    cursor = conn.cursor()
    for table in tables:
        cursor.execute(f'PRAGMA table_info("{table}")')
        rows = cursor.fetchall()
        schemas[table] = [
            {"name": row[1], "type": row[2], "notnull": bool(row[3])}
            for row in rows
        ]
    return schemas


def _get_all_table_names(conn: sqlite3.Connection) -> set[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cursor.fetchall()}


def _check_safety(sql: str) -> list[str]:
    """Return a list of forbidden keyword matches found in the SQL."""
    matches = _FORBIDDEN_KEYWORDS.findall(sql)
    return list(set(matches))


def _validate_sql(sql: str, conn: sqlite3.Connection, recommended_tables: list[str]) -> list[str]:
    """
    Run basic validation checks on the SQL string.
    Returns a list of error messages (empty = valid).
    """
    errors = []

    # Safety check
    forbidden = _check_safety(sql)
    if forbidden:
        errors.append(f"SQL contains forbidden keyword(s): {', '.join(forbidden)}. Only SELECT statements are allowed.")
        return errors  # Don't bother with further checks

    # Check that referenced tables exist
    all_tables = _get_all_table_names(conn)
    # Extract table names from FROM / JOIN clauses (simple heuristic)
    referenced = re.findall(
        r'(?:FROM|JOIN)\s+"?(\w+)"?', sql, re.IGNORECASE
    )
    for t in referenced:
        if t not in all_tables:
            errors.append(f"Table '{t}' does not exist in the database.")

    # Try EXPLAIN to catch syntax errors without executing
    if not errors:
        try:
            conn.execute(f"EXPLAIN {sql}")
        except sqlite3.Error as e:
            errors.append(f"SQL syntax error: {e}")

    return errors


def _extract_sql(text: str) -> str:
    """Extract the SQL query from Claude's response (strip code fences if present)."""
    # Look for ```sql ... ``` block first
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # If no fences, return stripped text
    return text.strip()


# ─────────────────────────────────────────────
# Prompt construction
# ─────────────────────────────────────────────

def _build_system_prompt(
    user_question: str,
    table_recommendations: dict,
    schemas: dict,
    domain: dict,
    data_dict: dict,
) -> str:
    """Build the system prompt for SQL generation."""
    recommended_tables = table_recommendations.get("recommended_tables", [])
    suggested_joins = table_recommendations.get("suggested_joins", [])
    relevant_columns = table_recommendations.get("relevant_columns", {})

    # Schema block
    schema_lines = []
    for table in recommended_tables:
        cols = schemas.get(table, [])
        col_descs = []
        for col in cols:
            key = f"{table}.{col['name']}"
            desc = data_dict.get(key, {}).get("description", "")
            sample = data_dict.get(key, {}).get("sample_values", [])
            sample_str = f" (e.g. {', '.join(str(s) for s in sample[:3])})" if sample else ""
            col_descs.append(f"    {col['name']} {col['type']}{sample_str}  -- {desc}")
        schema_lines.append(f"Table: {table}\n" + "\n".join(col_descs))

    # Suggested joins
    join_lines = [
        f"  {j['type']} ON {j['left']} = {j['right']}"
        for j in suggested_joins
    ]

    # Domain business rules
    rules = "\n".join(f"  - {r}" for r in domain.get("business_rules", []))

    # Relevant metric SQL patterns
    metric_patterns = []
    for metric_name, metric_info in domain.get("metrics", {}).items():
        needed = set(metric_info.get("tables_needed", []))
        if needed & set(recommended_tables):
            pattern = metric_info.get("sql_pattern", "")
            if pattern:
                metric_patterns.append(f"  -- {metric_name}\n  {pattern}")

    schema_block = "\n\n".join(schema_lines)
    joins_block = "\n".join(join_lines) if join_lines else "  (determine joins from schema)"
    patterns_block = "\n".join(metric_patterns) if metric_patterns else "  (no specific patterns)"

    return f"""You are an expert SQLite analyst for the Olist Brazilian e-commerce dataset.
Generate a single, correct SQLite SELECT query to answer the user's question.

## TABLE SCHEMAS (use ONLY these tables)

{schema_block}

## SUGGESTED JOIN CONDITIONS

{joins_block}

## BUSINESS RULES

{rules}

## REFERENCE SQL PATTERNS

{patterns_block}

## INSTRUCTIONS

1. Write a single SQLite-compatible SELECT query only — no DROP, DELETE, UPDATE, INSERT, ALTER, or CREATE
2. Use table aliases for readability (e.g. o for orders, i for items)
3. Include inline SQL comments (--) explaining each major clause
4. Use ROUND(..., 2) for monetary values
5. Add a LIMIT clause when returning ranked/top results (default LIMIT 20 unless user specifies)
6. Always qualify column names with table alias when joining multiple tables
7. Use strftime('%Y-%m', column) for monthly grouping
8. Use COUNT(DISTINCT ...) when counting unique entities
9. Return ONLY the SQL query — no explanation, no markdown, no code fences
"""


def _build_correction_prompt(sql: str, errors: list[str]) -> str:
    """Build a correction prompt when validation or execution fails."""
    error_list = "\n".join(f"  - {e}" for e in errors)
    return f"""The following SQL query failed validation or execution:

```sql
{sql}
```

Errors:
{error_list}

Please fix the SQL query. Return ONLY the corrected SQL — no explanation, no markdown, no code fences.
"""


# ─────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────

def generate_and_run_sql(user_question: str, table_recommendations: dict) -> dict:
    """
    Generate SQL for the user question, validate it, self-correct if needed,
    and execute it against the SQLite database.

    Args:
        user_question: Natural language question from the user.
        table_recommendations: Output from recommend_tables().

    Returns:
        dict with keys: sql_query, sql_explanation, results (DataFrame),
                        row_count, column_names, execution_time_ms, errors
    """
    domain = _load_json(DOMAIN_KNOWLEDGE_PATH)
    data_dict = _load_json(DATA_DICTIONARY_PATH)

    conn = sqlite3.connect(DATABASE_PATH)
    recommended_tables = table_recommendations.get("recommended_tables", [])
    schemas = _get_table_schemas(conn, recommended_tables)

    system_prompt = _build_system_prompt(
        user_question, table_recommendations, schemas, domain, data_dict
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Initial SQL generation
    messages = [{"role": "user", "content": f"Question: {user_question}"}]
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )
    sql = _extract_sql(message.content[0].text)

    # Validation + self-correction loop
    errors: list[str] = []
    for attempt in range(MAX_RETRIES):
        errors = _validate_sql(sql, conn, recommended_tables)
        if not errors:
            break

        if attempt < MAX_RETRIES - 1:
            # Send error back to Claude for self-correction
            messages.append({"role": "assistant", "content": sql})
            messages.append({"role": "user", "content": _build_correction_prompt(sql, errors)})
            correction = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            )
            sql = _extract_sql(correction.content[0].text)

    if errors:
        conn.close()
        return {
            "sql_query": sql,
            "sql_explanation": "",
            "results": pd.DataFrame(),
            "row_count": 0,
            "column_names": [],
            "execution_time_ms": 0,
            "errors": errors,
        }

    # Execute the validated SQL
    start = time.monotonic()
    try:
        df = pd.read_sql_query(sql, conn)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        execution_errors: list[str] = []
    except Exception as e:
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        df = pd.DataFrame()
        execution_errors = [str(e)]

    conn.close()

    # Ask Claude for a plain-English explanation of the SQL
    explanation = ""
    if not execution_errors:
        exp_message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": (
                    f"In 1-2 sentences, explain what this SQL query does in plain English "
                    f"for a business analyst (no technical jargon):\n\n{sql}"
                ),
            }],
        )
        explanation = exp_message.content[0].text.strip()

    return {
        "sql_query": sql,
        "sql_explanation": explanation,
        "results": df,
        "row_count": len(df),
        "column_names": list(df.columns),
        "execution_time_ms": elapsed_ms,
        "errors": execution_errors,
    }


if __name__ == "__main__":
    import sys
    from agents.table_recommender import recommend_tables

    q = sys.argv[1] if len(sys.argv) > 1 else "What are the top 5 product categories by total revenue?"
    recs = recommend_tables(q)
    result = generate_and_run_sql(q, recs)
    print("SQL:", result["sql_query"])
    print("Explanation:", result["sql_explanation"])
    print("Rows returned:", result["row_count"])
    if not result["results"].empty:
        print(result["results"].head(10).to_string())
    if result["errors"]:
        print("Errors:", result["errors"])
